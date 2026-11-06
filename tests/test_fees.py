"""Unit and integration tests for the Municipal Fee Engine (PS-115).

Covers:
- Reusable rounding helper (round_up_to_nearest_10)
- Scrutiny fee (minimum cap and rate per sq.m)
- Development charge (residential, commercial, mixed-use floor breakdown)
- Premium FAR fee (residential 40%, commercial 60%, mixed-use 40%)
- Betterment levy (agri-converted 2% vs non-agri)
- Labour cess (1% of construction cost at Rs 1,800/sq.ft)
- Parking shortfall fee (Rs 200,000/car)
- Gating logic (refusal upon non-compoundable violations)
- Exact verification against all 27 official FEE_PAYMENT records in commands.txt
"""

from __future__ import annotations

import pathlib
import pytest

from src.data_loader import load_data_pack
from src.fees import (
    calculate_betterment_levy,
    calculate_development_charge,
    calculate_fee_demand,
    calculate_labour_cess,
    calculate_parking_shortfall_fee,
    calculate_premium_far_fee,
    calculate_scrutiny_fee,
    round_up_to_nearest_10,
)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def data_pack():
    """Load the full official dataset once for fee verification."""
    return load_data_pack(DATA_DIR)


# ==============================================================================
# 1. Rounding Helper Tests
# ==============================================================================

def test_round_up_to_nearest_10_exact_multiples():
    """Exact multiples of 10 must remain unchanged."""
    assert round_up_to_nearest_10(0.0) == 0.0
    assert round_up_to_nearest_10(10.0) == 10.0
    assert round_up_to_nearest_10(5040.0) == 5040.0
    assert round_up_to_nearest_10(75600.0) == 75600.0


def test_round_up_to_nearest_10_fractional_and_midpoint():
    """Any amount above a multiple of 10 rounds up to the next 10."""
    assert round_up_to_nearest_10(10.01) == 20.0
    assert round_up_to_nearest_10(13489.8) == 13490.0
    assert round_up_to_nearest_10(48825.0504) == 48830.0
    assert round_up_to_nearest_10(1.0) == 10.0


def test_round_up_to_nearest_10_invalid_inputs():
    """Helper rejects negative numbers, booleans, and non-numeric types."""
    with pytest.raises(ValueError, match="cannot be negative"):
        round_up_to_nearest_10(-5.0)

    with pytest.raises(TypeError, match="must be a number"):
        round_up_to_nearest_10(True)  # type: ignore

    with pytest.raises(TypeError, match="must be a number"):
        round_up_to_nearest_10("100")  # type: ignore


# ==============================================================================
# 2. Scrutiny Fee Tests
# ==============================================================================

def test_calculate_scrutiny_fee_minimum_cap():
    """Small built-up area triggers the Rs 2,000 minimum fee cap."""
    # 50 sq.m * Rs 20 = Rs 1,000 < Rs 2,000 minimum
    assert calculate_scrutiny_fee(50.0) == 2000.0
    assert calculate_scrutiny_fee(0.0) == 2000.0
    # Exactly 100 sq.m * Rs 20 = Rs 2,000
    assert calculate_scrutiny_fee(100.0) == 2000.0


def test_calculate_scrutiny_fee_above_minimum():
    """Area above 100 sq.m scales at Rs 20/sq.m and rounds up to next Rs 10."""
    # 252.0 * 20 = 5040.0 (exact multiple of 10)
    assert calculate_scrutiny_fee(252.0) == 5040.0
    # 674.49 * 20 = 13489.8 -> rounds up to 13490.0
    assert calculate_scrutiny_fee(674.49) == 13490.0


def test_calculate_scrutiny_fee_invalid_inputs():
    """Rejects negative area or invalid types."""
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_scrutiny_fee(-10.0)
    with pytest.raises(TypeError, match="must be a number"):
        calculate_scrutiny_fee(False)  # type: ignore


# ==============================================================================
# 3. Development Charge Tests
# ==============================================================================

def test_calculate_development_charge_pure_residential():
    """Pure residential buildings are charged Rs 300 per sq.m across all floors."""
    # 252.0 sq.m * 300 = 75600.0
    assert calculate_development_charge("RESIDENTIAL", 252.0) == 75600.0
    # 674.49 sq.m * 300 = 202347.0 -> rounds up to 202350.0
    assert calculate_development_charge("residential", 674.49) == 202350.0


def test_calculate_development_charge_pure_commercial():
    """Pure commercial buildings are charged Rs 600 per sq.m across all floors."""
    # 1000.0 sq.m * 600 = 600000.0
    assert calculate_development_charge("COMMERCIAL", 1000.0) == 600000.0
    # 123.45 sq.m * 600 = 74070.0
    assert calculate_development_charge("commercial", 123.45) == 74070.0


def test_calculate_development_charge_mixed_use_floor_breakdown():
    """Mixed-use buildings charge commercial floors @ Rs 600 and others @ Rs 300."""
    # APP-0007 scenario: Total 408 sq.m, 136 commercial, 136 residential, 136 parking
    # (136 * 600) + ((408 - 136) * 300) = 81600 + 81600 = 163200.0
    floors = [
        {"floor_no": "G", "floor_use": "PARKING", "built_up_sqm": 136.0},
        {"floor_no": "1", "floor_use": "COMMERCIAL", "built_up_sqm": 136.0},
        {"floor_no": "2", "floor_use": "RESIDENTIAL", "built_up_sqm": 136.0},
    ]
    charge = calculate_development_charge("MIXED", 408.0, floors_data=floors)
    assert charge == 163200.0


def test_calculate_development_charge_mixed_use_requires_floors_data():
    """Mixed-use development charge requires floor-level data."""
    with pytest.raises(ValueError, match="floors_data is required"):
        calculate_development_charge("MIXED", 408.0, floors_data=None)


def test_calculate_development_charge_invalid_inputs():
    """Rejects unknown building use and negative area."""
    with pytest.raises(ValueError, match="Unsupported proposed_use"):
        calculate_development_charge("INDUSTRIAL", 500.0)
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_development_charge("RESIDENTIAL", -50.0)


# ==============================================================================
# 4. Premium FAR Fee Tests
# ==============================================================================

def test_calculate_premium_far_fee_zero_requested():
    """Zero premium FAR requested yields zero fee."""
    assert calculate_premium_far_fee(0.0, 405.0, 94000.0, "RESIDENTIAL") == 0.0


def test_calculate_premium_far_fee_residential_40pct():
    """Residential premium FAR fee is 40% of guidance value on chargeable area."""
    # APP-0002 scenario: 0.25 premium FAR, plot 405 sq.m, GV 94000
    # Chargeable area = 0.25 * 405 = 101.25 sq.m
    # Fee = 101.25 * 94000 * 0.40 = 3807000.0
    fee = calculate_premium_far_fee(0.25, 405.0, 94000.0, "RESIDENTIAL")
    assert fee == 3807000.0


def test_calculate_premium_far_fee_commercial_60pct():
    """Commercial premium FAR fee is 60% of guidance value on chargeable area."""
    # 0.50 premium FAR, plot 500 sq.m, GV 100000
    # Chargeable area = 0.50 * 500 = 250 sq.m
    # Fee = 250 * 100000 * 0.60 = 15000000.0
    fee = calculate_premium_far_fee(0.50, 500.0, 100000.0, "COMMERCIAL")
    assert fee == 15000000.0


def test_calculate_premium_far_fee_mixed_use_40pct():
    """Mixed-use premium FAR fee uses 40% (evidence-based from 27-payment audit)."""
    # 0.20 premium FAR, plot 300 sq.m, GV 50000
    # Chargeable area = 60 sq.m
    # Fee = 60 * 50000 * 0.40 = 1200000.0
    fee = calculate_premium_far_fee(0.20, 300.0, 50000.0, "MIXED")
    assert fee == 1200000.0


def test_calculate_premium_far_fee_invalid_inputs():
    """Rejects negative values and non-numeric inputs."""
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_premium_far_fee(-0.1, 400.0, 50000.0, "RESIDENTIAL")
    with pytest.raises(ValueError, match="must be greater than zero"):
        calculate_premium_far_fee(0.2, 0.0, 50000.0, "RESIDENTIAL")


# ==============================================================================
# 5. Betterment Levy Tests
# ==============================================================================

def test_calculate_betterment_levy_non_agri_is_zero():
    """Non-agricultural land incurs zero betterment levy."""
    assert calculate_betterment_levy(False, 500.0, 50000.0) == 0.0


def test_calculate_betterment_levy_agri_converted():
    """Agri-converted land incurs 2% of total plot guidance value."""
    # APP-0001: plot 157.5 sq.m, GV 54300.0
    # Total plot guidance value = 157.5 * 54300 = 8552250.0
    # 2% = 171045.0 -> rounds up to 171050.0
    assert calculate_betterment_levy(True, 157.5, 54300.0) == 171050.0

    # APP-0002: plot 405.0 sq.m, GV 94000.0
    # Total plot GV = 38070000.0 * 0.02 = 761400.0 (exact multiple of 10)
    assert calculate_betterment_levy(True, 405.0, 94000.0) == 761400.0


def test_calculate_betterment_levy_invalid_inputs():
    """Rejects non-boolean agri_converted or negative dimensions."""
    with pytest.raises(TypeError, match="must be a boolean"):
        calculate_betterment_levy("true", 100.0, 1000.0)  # type: ignore
    with pytest.raises(ValueError, match="must be greater than zero"):
        calculate_betterment_levy(True, 0.0, 1000.0)


# ==============================================================================
# 6. Labour Cess Tests
# ==============================================================================

def test_calculate_labour_cess_standard():
    """1% of construction cost at Rs 1,800/sq.ft (1 sq.m = 10.7639 sq.ft)."""
    # APP-0005: total built-up = 252.0 sq.m
    # Cost = 252.0 * 10.7639 * 1800 = 4882505.04
    # 1% cess = 48825.0504 -> rounds up to 48830.0
    assert calculate_labour_cess(252.0) == 48830.0

    # APP-0001: total built-up = 330.75 sq.m
    # Cost = 330.75 * 10.7639 * 1800 = 6408104.73
    # 1% cess = 64081.0473 -> rounds up to 64090.0
    assert calculate_labour_cess(330.75) == 64090.0


def test_calculate_labour_cess_invalid_inputs():
    """Rejects negative built-up area and non-numeric types."""
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_labour_cess(-10.0)
    with pytest.raises(TypeError, match="must be a number"):
        calculate_labour_cess(None)  # type: ignore


# ==============================================================================
# 7. Parking Shortfall Fee Tests
# ==============================================================================

def test_calculate_parking_shortfall_fee():
    """Charges Rs 200,000 per missing car for allowable shortfall."""
    assert calculate_parking_shortfall_fee(0.0) == 0.0
    # APP-0017 scenario: 2 missing cars = Rs 400,000.0
    assert calculate_parking_shortfall_fee(2.0) == 400000.0
    assert calculate_parking_shortfall_fee(1.0) == 200000.0


def test_calculate_parking_shortfall_fee_invalid_inputs():
    """Rejects negative shortfall cars."""
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_parking_shortfall_fee(-1.0)


# ==============================================================================
# 8. Fee Demand Assembler and Gating Tests
# ==============================================================================

def test_calculate_fee_demand_gating_refuses_on_fatal_violation(data_pack):
    """Fee demand must return None if non-compoundable violations are present."""
    app_0003 = next(a for a in data_pack["applications"] if a["app_id"] == "APP-0003")
    floors = data_pack["floors_by_app"]["APP-0003"]
    # Non-compoundable FAR cap violation
    mock_fatal_violations = [{"passed": False, "rule_id": "FAR_CAP", "compoundable": False}]
    demand = calculate_fee_demand(app_0003, floors, validation_results=mock_fatal_violations)
    assert demand is None


def test_calculate_fee_demand_permits_compoundable_violation(data_pack):
    """Fee demand is generated when only compoundable violations exist."""
    app_0001 = next(a for a in data_pack["applications"] if a["app_id"] == "APP-0001")
    floors = data_pack["floors_by_app"]["APP-0001"]
    # Compoundable setback deviation (<= 0.3m)
    mock_compoundable = [{"passed": False, "rule_id": "SETBACK_FRONT", "compoundable": True}]
    demand = calculate_fee_demand(app_0001, floors, validation_results=mock_compoundable)
    assert demand is not None
    assert demand["app_id"] == "APP-0001"
    assert demand["total_fee"] == 340990.0


def test_calculate_fee_demand_exact_schema(data_pack):
    """Verify that calculate_fee_demand returns exact columns in expected order."""
    app_0005 = next(a for a in data_pack["applications"] if a["app_id"] == "APP-0005")
    floors = data_pack["floors_by_app"]["APP-0005"]
    demand = calculate_fee_demand(app_0005, floors)

    expected_keys = [
        "app_id",
        "built_up_sqm",
        "far_area_sqm",
        "far_achieved",
        "far_allowed",
        "scrutiny_fee",
        "development_charge",
        "premium_far_fee",
        "betterment_levy",
        "labour_cess",
        "parking_shortfall_fee",
        "total_fee",
    ]
    assert list(demand.keys()) == expected_keys
    assert demand["app_id"] == "APP-0005"
    assert demand["built_up_sqm"] == 252.0
    assert demand["far_area_sqm"] == 250.24  # 252.0 - 10% of 17.64 balcony
    assert demand["total_fee"] == 129470.0


# ==============================================================================
# 9. Complete Verification Against All 27 Official FEE_PAYMENT Records
# ==============================================================================

def test_all_27_official_fee_payments_match_exact_rupee(data_pack):
    """Exhaustively verify calculate_fee_demand against every initial fee payment in commands.txt.

    This test extracts all initial FEE_PAYMENT records from commands.txt and asserts
    that our fee engine calculates the EXACT total amount to the rupee with 0.0 diff.
    """
    commands_path = DATA_DIR / "commands.txt"
    initial_payments: dict[str, float] = {}

    for line in commands_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("FEE_PAYMENT|"):
            parts = line.split("|")
            app_id = parts[1]
            amount = float(parts[3])
            # Store initial payment only (e.g. for APP-0023, the initial plan approval fee)
            if app_id not in initial_payments:
                initial_payments[app_id] = amount

    assert len(initial_payments) == 27, f"Expected 27 fee payments, found {len(initial_payments)}"

    apps_by_id = {a["app_id"]: a for a in data_pack["applications"]}
    floors_by_app = data_pack["floors_by_app"]

    for app_id, expected_payment in initial_payments.items():
        app = apps_by_id[app_id]
        floors = floors_by_app[app_id]

        # Calculate parking shortfall if any
        comm_bua = sum(f["built_up_sqm"] for f in floors if f["floor_use"] == "COMMERCIAL")
        u_gt = app["units_carpet_above_100"]
        u_le = app["units_carpet_upto_100"]
        req_cars = (u_gt * 1.0) + (u_le * 0.5) + (comm_bua / 50.0)
        shortfall = max(0.0, req_cars - app["parking_proposed"])

        demand = calculate_fee_demand(app, floors, parking_shortfall_cars=shortfall)
        assert demand is not None, f"Fee demand was unexpectedly refused for {app_id}"
        calculated_total = demand["total_fee"]

        diff = abs(calculated_total - expected_payment)
        assert diff == 0.0, (
            f"Fee mismatch for {app_id} ({app['proposed_use']}): "
            f"Calculated Rs {calculated_total:.2f} != Expected Rs {expected_payment:.2f} (Diff: Rs {diff:.2f})\n"
            f"Breakdown: {demand}"
        )
