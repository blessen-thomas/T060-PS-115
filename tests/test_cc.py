"""Unit and integration tests for Completion Certificate (CC) Engine (PS-115).

Covers:
- Built-up area deviation slabs (<=5% @ 2x, >5% to <=10% @ 4x, >10% non-compoundable)
- Setback deviation compounding (<=0.30m @ Rs 10,000/metre-side, >0.30m non-compoundable)
- Height deviation (strictly non-compoundable)
- Verification of all 6 official CC_REQUEST planted cases:
  1. APP-0013: +0.40m height deviation -> CC_REFUSED
  2. APP-0010: 0.30m setback on 2 sides -> CC_ISSUED (Rs 6,000)
  3. APP-0009: exactly +5.00% built-up -> CC_ISSUED (2x slab, Rs 8,190)
  4. APP-0002: clean as-built -> CC_ISSUED (Rs 0)
  5. APP-0006: +12.00% built-up -> CC_REFUSED (exceeds 10% ceiling)
  6. APP-0007: exactly +10.00% built-up -> CC_ISSUED (4x slab)
- Integration processing of CC_REQUEST commands from commands.txt
"""

from __future__ import annotations

import pathlib
import pytest

from src.cc import (
    calculate_area_compounding_fee,
    calculate_built_up_deviation,
    calculate_setback_compounding_fee,
    evaluate_cc_request,
    process_cc_commands,
)
from src.data_loader import load_data_pack

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def data_pack():
    """Load the full official dataset once."""
    return load_data_pack(DATA_DIR)


# ==============================================================================
# 1. Built-Up Area Deviation Calculation Tests
# ==============================================================================

def test_calculate_built_up_deviation_clean():
    """As-built area less than or equal to approved area yields zero deviation."""
    excess, pct = calculate_built_up_deviation(500.0, 500.0)
    assert excess == 0.0
    assert pct == 0.0

    excess_under, pct_under = calculate_built_up_deviation(500.0, 480.0)
    assert excess_under == 0.0
    assert pct_under == 0.0


def test_calculate_built_up_deviation_exact_slabs():
    """Verify exact 5.00% and 10.00% slab boundaries from official planted cases."""
    # APP-0009: approved 273.00, as-built 286.65 = exactly +5.00%
    excess_0009, pct_0009 = calculate_built_up_deviation(273.0, 286.65)
    assert excess_0009 == 13.65
    assert pct_0009 == 5.00

    # APP-0007: approved 408.00, as-built 448.80 = exactly +10.00%
    excess_0007, pct_0007 = calculate_built_up_deviation(408.0, 448.80)
    assert excess_0007 == 40.80
    assert pct_0007 == 10.00

    # APP-0006: approved 609.18, as-built 682.28 = exactly +12.00%
    excess_0006, pct_0006 = calculate_built_up_deviation(609.18, 682.28)
    assert excess_0006 == 73.10
    assert pct_0006 == 12.00


# ==============================================================================
# 2. Area Compounding Fee Calculation Tests
# ==============================================================================

def test_calculate_area_compounding_fee_slabs():
    """Verify 2x and 4x slabs and rejection over 10%."""
    # 5.0% deviation on 13.65 sq.m excess @ Rs 300/sq.m = 2 * 300 * 13.65 = Rs 8,190.0
    fee_5pct = calculate_area_compounding_fee(13.65, 5.00, dev_charge_rate=300.0)
    assert fee_5pct == 8190.0

    # 10.0% deviation on 40.80 sq.m excess @ Rs 400/sq.m = 4 * 400 * 40.80 = Rs 65,280.0
    fee_10pct = calculate_area_compounding_fee(40.80, 10.00, dev_charge_rate=400.0)
    assert fee_10pct == 65280.0

    # Over 10% raises ValueError
    with pytest.raises(ValueError, match="exceeds 10% maximum compounding ceiling"):
        calculate_area_compounding_fee(73.10, 12.00, dev_charge_rate=300.0)


# ==============================================================================
# 3. Setback Compounding Fee Tests
# ==============================================================================

def test_calculate_setback_compounding_fee_boundaries():
    """Verify Rs 10,000/metre-side up to 0.30m, and rejection above 0.30m."""
    # 0.0m deviation = Rs 0.0
    assert calculate_setback_compounding_fee(0.0, 0) == 0.0

    # APP-0010: 0.30m deviation on 2 sides = 10000 * 0.30 * 2 = Rs 6,000.0
    fee_0010 = calculate_setback_compounding_fee(0.30, 2)
    assert fee_0010 == 6000.0

    # Above 0.30m (e.g. 0.31m) raises ValueError
    with pytest.raises(ValueError, match="exceeds 0.30m maximum compounding tolerance"):
        calculate_setback_compounding_fee(0.31, 1)


# ==============================================================================
# 4. Official Planted CC_REQUEST Test Cases
# ==============================================================================

def test_app_0013_height_deviation_refused():
    """Official scenario: APP-0013 as-built height +0.40m -> CC_REFUSED even with clean area/setbacks."""
    res = evaluate_cc_request(
        app_id="APP-0013",
        request_date="2026-09-22",
        approved_built_up_sqm=292.50,
        as_built_built_up_sqm=292.50,
        approved_height_m=9.60,
        as_built_height_m=10.00,  # +0.40m deviation
        setback_deviation_m=0.00,
        sides_deviating=0,
    )
    assert res["decision"] == "CC_REFUSED"
    assert res["height_deviation_m"] == "0.40"
    assert res["deviation_pct"] == "0.00"
    assert res["area_compounding_fee"] == 0.0
    assert res["setback_compounding_fee"] == 0.0


def test_app_0010_setback_compounded_issued():
    """Official scenario: APP-0010 0.30m setback deviation on 2 sides -> CC_ISSUED with Rs 6,000 fee."""
    res = evaluate_cc_request(
        app_id="APP-0010",
        request_date="2026-09-23",
        approved_built_up_sqm=770.50,
        as_built_built_up_sqm=770.50,
        approved_height_m=16.00,
        as_built_height_m=16.00,
        setback_deviation_m=0.30,
        sides_deviating=2,
    )
    assert res["decision"] == "CC_ISSUED"
    assert res["setback_compounding_fee"] == 6000.0
    assert res["area_compounding_fee"] == 0.0
    assert res["height_deviation_m"] == "0.00"


def test_app_0009_5pct_slab_compounded_issued():
    """Official scenario: APP-0009 exactly +5.00% built-up -> CC_ISSUED with 2x slab (Rs 8,190)."""
    res = evaluate_cc_request(
        app_id="APP-0009",
        request_date="2026-09-26",
        approved_built_up_sqm=273.00,
        as_built_built_up_sqm=286.65,
        approved_height_m=9.60,
        as_built_height_m=9.60,
        dev_charge_rate=300.0,
    )
    assert res["decision"] == "CC_ISSUED"
    assert res["deviation_pct"] == "5.00"
    assert res["area_compounding_fee"] == 8190.0
    assert res["setback_compounding_fee"] == 0.0


def test_app_0002_clean_as_built_issued():
    """Official scenario: APP-0002 clean as-built -> CC_ISSUED with zero fees."""
    res = evaluate_cc_request(
        app_id="APP-0002",
        request_date="2026-10-02",
        approved_built_up_sqm=1006.25,
        as_built_built_up_sqm=1006.25,
        approved_height_m=16.00,
        as_built_height_m=16.00,
    )
    assert res["decision"] == "CC_ISSUED"
    assert res["deviation_pct"] == "0.00"
    assert res["area_compounding_fee"] == 0.0
    assert res["setback_compounding_fee"] == 0.0


def test_app_0006_excess_12pct_refused():
    """Official scenario: APP-0006 +12% built-up exceeds 10% ceiling -> CC_REFUSED."""
    res = evaluate_cc_request(
        app_id="APP-0006",
        request_date="2026-10-06",
        approved_built_up_sqm=609.18,
        as_built_built_up_sqm=682.28,
        approved_height_m=9.60,
        as_built_height_m=9.60,
    )
    assert res["decision"] == "CC_REFUSED"
    assert res["deviation_pct"] == "12.00"
    assert res["area_compounding_fee"] == 0.0


def test_app_0007_10pct_slab_compounded_issued():
    """Official scenario: APP-0007 exactly +10.00% built-up -> CC_ISSUED with 4x slab."""
    # Mixed-use building with effective dev rate = 400.0/sq.m
    res = evaluate_cc_request(
        app_id="APP-0007",
        request_date="2026-10-21",
        approved_built_up_sqm=408.00,
        as_built_built_up_sqm=448.80,
        approved_height_m=9.60,
        as_built_height_m=9.60,
        dev_charge_rate=400.0,
    )
    assert res["decision"] == "CC_ISSUED"
    assert res["deviation_pct"] == "10.00"
    assert res["area_compounding_fee"] == 65280.0


# ==============================================================================
# 5. Full Command Processing Integration Test
# ==============================================================================

def test_process_cc_commands_from_file(data_pack):
    """Process all CC_REQUEST commands from commands.txt and verify exact decisions."""
    commands_path = DATA_DIR / "commands.txt"
    commands = commands_path.read_text().splitlines()

    results = process_cc_commands(
        commands=commands,
        applications=data_pack["applications"],
        floors_by_app=data_pack["floors_by_app"],
    )

    assert len(results) == 6

    # Verify decision schema on every row
    expected_cols = [
        "app_id",
        "request_date",
        "deviation_pct",
        "area_compounding_fee",
        "setback_compounding_fee",
        "height_deviation_m",
        "decision",
    ]
    for row in results:
        assert list(row.keys()) == expected_cols

    # Verify specific outcomes
    decisions_by_app = {r["app_id"]: r for r in results}
    assert decisions_by_app["APP-0013"]["decision"] == "CC_REFUSED"
    assert decisions_by_app["APP-0010"]["decision"] == "CC_ISSUED"
    assert decisions_by_app["APP-0009"]["decision"] == "CC_ISSUED"
    assert decisions_by_app["APP-0002"]["decision"] == "CC_ISSUED"
    assert decisions_by_app["APP-0006"]["decision"] == "CC_REFUSED"
    assert decisions_by_app["APP-0007"]["decision"] == "CC_ISSUED"
