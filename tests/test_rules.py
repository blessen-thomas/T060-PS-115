"""Unit Tests for Municipal Rule Validation Engine (src/rules.py)."""

from pathlib import Path
import pytest

from src.data_loader import (
    load_applications,
    load_coverage_table,
    load_setback_table,
    load_zones,
)
from src.rules import (
    check_all_setbacks,
    check_front_setback,
    check_ground_coverage,
    check_rear_setback,
    check_side_setback_1,
    check_side_setback_2,
    check_zoning_use,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def zones():
    """Load the official zones table from data/zones.csv."""
    return load_zones(DATA_DIR / "zones.csv")


@pytest.fixture
def applications():
    """Load official applications from data/applications.csv."""
    return load_applications(DATA_DIR / "applications.csv")


@pytest.fixture
def coverage_table():
    """Load the official coverage table from data/coverage_table.csv."""
    return load_coverage_table(DATA_DIR / "coverage_table.csv")


@pytest.fixture
def setback_table():
    """Load the official setback table from data/setback_table.csv."""
    return load_setback_table(DATA_DIR / "setback_table.csv")


# ==============================================================================
# 1. Zoning & Permitted Use Validation Tests (ZONING_USE)
# ==============================================================================

def test_check_zoning_use_permitted_passes(zones):
    """Permitted use in zone should pass validation."""
    # ZN-R1 permits RESIDENTIAL
    result = check_zoning_use("ZN-R1", "RESIDENTIAL", zones)
    assert result["passed"] is True
    assert result["rule_id"] == "ZONING_USE"
    assert result["proposed"] == "RESIDENTIAL"
    assert result["required"] == "RESIDENTIAL"
    assert result["compoundable"] is False

    # ZN-C1 permits COMMERCIAL;MIXED
    result_comm = check_zoning_use("ZN-C1", "COMMERCIAL", zones)
    assert result_comm["passed"] is True

    result_mix = check_zoning_use("ZN-C1", "MIXED", zones)
    assert result_mix["passed"] is True


def test_check_zoning_use_violation_fails(zones):
    """Unpermitted use in zone should fail validation."""
    # ZN-R1 does NOT permit COMMERCIAL
    result = check_zoning_use("ZN-R1", "COMMERCIAL", zones)
    assert result["passed"] is False
    assert result["rule_id"] == "ZONING_USE"
    assert result["proposed"] == "COMMERCIAL"
    assert result["required"] == "RESIDENTIAL"
    assert result["compoundable"] is False


def test_check_zoning_use_unknown_zone_handled(zones):
    """Unknown zone ID is safely handled without unhandled crashes."""
    result = check_zoning_use("ZN-NONEXISTENT", "RESIDENTIAL", zones)
    assert result["passed"] is False
    assert "Unknown zone" in result["proposed"]

    # When raise_on_unknown_zone is requested, ValueError is raised
    with pytest.raises(ValueError, match="Unknown zone_id"):
        check_zoning_use("ZN-NONEXISTENT", "RESIDENTIAL", zones, raise_on_unknown_zone=True)


def test_check_zoning_use_app_0032_planted_case(zones, applications):
    """Official planted scenario: APP-0032 proposes COMMERCIAL in ZN-R1 (residential only).

    Must be reported as a non-compoundable ZONING_USE violation.
    """
    app_0032 = next(a for a in applications if a["app_id"] == "APP-0032")
    assert app_0032["zone_id"] == "ZN-R1"
    assert app_0032["proposed_use"] == "COMMERCIAL"

    result = check_zoning_use(app_0032["zone_id"], app_0032["proposed_use"], zones)
    assert result["passed"] is False
    assert result["rule_id"] == "ZONING_USE"
    assert result["proposed"] == "COMMERCIAL"
    assert result["required"] == "RESIDENTIAL"
    assert result["compoundable"] is False


# ==============================================================================
# 2. Ground Coverage Validation Tests (GROUND_COVERAGE)
# ==============================================================================

def test_check_ground_coverage_passes(coverage_table):
    """Footprint within max allowed coverage passes."""
    # Plot 100 sq.m (band <= 200 sq.m -> max 65%), footprint 50 sq.m (50% <= 65%)
    result = check_ground_coverage(50.0, 100.0, coverage_table)
    assert result["passed"] is True
    assert result["rule_id"] == "GROUND_COVERAGE"
    assert result["required"] == "65.00%"
    assert result["proposed"] == "50.00%"
    assert result["compoundable"] is False


def test_check_ground_coverage_violation_fails(coverage_table):
    """Footprint exceeding max allowed coverage fails."""
    # Plot 100 sq.m (band <= 200 sq.m -> max 65%), footprint 70 sq.m (70% > 65%)
    result = check_ground_coverage(70.0, 100.0, coverage_table)
    assert result["passed"] is False
    assert result["rule_id"] == "GROUND_COVERAGE"
    assert result["required"] == "65.00%"
    assert result["proposed"] == "70.00%"
    assert result["compoundable"] is False


def test_check_ground_coverage_exact_boundary_passes(coverage_table):
    """Footprint exactly equal to the permitted percentage is compliant."""
    # Plot 200 sq.m, footprint 130 sq.m = exactly 65.00%
    result = check_ground_coverage(130.0, 200.0, coverage_table)
    assert result["passed"] is True
    assert result["required"] == "65.00%"
    assert result["proposed"] == "65.00%"


def test_check_ground_coverage_200sqm_band_distinction(coverage_table):
    """Exact boundary of 200 sq.m falls into the 65% band; 200.01 falls into 60% band."""
    # Plot = 200.00 sq.m, footprint = 126.00 sq.m -> 63.00% <= 65.00% (Passes)
    res_200 = check_ground_coverage(126.0, 200.0, coverage_table)
    assert res_200["passed"] is True
    assert res_200["required"] == "65.00%"

    # Plot = 200.01 sq.m, footprint = 126.00 sq.m -> 62.996% > 60.00% (Fails)
    res_200_01 = check_ground_coverage(126.0, 200.01, coverage_table)
    assert res_200_01["passed"] is False
    assert res_200_01["required"] == "60.00%"


def test_check_ground_coverage_invalid_inputs_rejected(coverage_table):
    """Invalid plot area or footprint values are rejected."""
    with pytest.raises(ValueError, match="Plot area must be greater than zero"):
        check_ground_coverage(50.0, 0.0, coverage_table)

    with pytest.raises(ValueError, match="Plot area must be greater than zero"):
        check_ground_coverage(50.0, -100.0, coverage_table)

    with pytest.raises(ValueError, match="Ground footprint area cannot be negative"):
        check_ground_coverage(-10.0, 200.0, coverage_table)

    with pytest.raises(TypeError, match="must be a number"):
        check_ground_coverage("50", 200.0, coverage_table)  # type: ignore

    with pytest.raises(TypeError, match="must be a number"):
        check_ground_coverage(True, 200.0, coverage_table)  # type: ignore


def test_check_ground_coverage_app_0014_planted_case(coverage_table, applications):
    """Official planted scenario: APP-0014 ground coverage breaches 60% limit.

    Plot = 450 sq.m, Footprint = 275 sq.m -> Coverage = 61.11% > 60.00%.
    Must be reported as a non-compoundable GROUND_COVERAGE violation.
    """
    app_0014 = next(a for a in applications if a["app_id"] == "APP-0014")
    assert app_0014["plot_area_sqm"] == 450.0
    assert app_0014["ground_footprint_sqm"] == 275.0

    result = check_ground_coverage(
        ground_footprint_sqm=app_0014["ground_footprint_sqm"],
        plot_area_sqm=app_0014["plot_area_sqm"],
        coverage_table=coverage_table,
    )
    assert result["passed"] is False
    assert result["rule_id"] == "GROUND_COVERAGE"
    assert result["required"] == "60.00%"
    assert result["proposed"] == "61.11%"
    assert result["compoundable"] is False


def test_check_ground_coverage_app_0005_planted_case(coverage_table, applications):
    """Official EC-02 scenario: APP-0005 plot 200 sq.m, footprint 126 sq.m.

    Coverage = 63.00% <= 65.00% -> Passes!
    """
    app_0005 = next(a for a in applications if a["app_id"] == "APP-0005")
    assert app_0005["plot_area_sqm"] == 200.0
    assert app_0005["ground_footprint_sqm"] == 126.0

    result = check_ground_coverage(
        ground_footprint_sqm=app_0005["ground_footprint_sqm"],
        plot_area_sqm=app_0005["plot_area_sqm"],
        coverage_table=coverage_table,
    )
    assert result["passed"] is True
    assert result["rule_id"] == "GROUND_COVERAGE"
    assert result["required"] == "65.00%"
    assert result["proposed"] == "63.00%"
    assert result["compoundable"] is False


# ==============================================================================
# 3. Setback Validation Tests (SETBACK_FRONT, SETBACK_SIDE1, SETBACK_SIDE2, SETBACK_REAR)
# ==============================================================================

# --- Front Setback Tests ---

def test_front_setback_three_bands(setback_table):
    """Verify front setback requirements across all three road width bands."""
    # Band 1: Road width < 12m -> 3.00m
    res1 = check_front_setback(3.0, 10.0, setback_table)
    assert res1["passed"] is True
    assert res1["rule_id"] == "SETBACK_FRONT"
    assert res1["required"] == "3.00m"
    assert res1["proposed"] == "3.00m"

    # Band 2: Road width 12m to 18m -> 4.50m
    res2 = check_front_setback(4.5, 15.0, setback_table)
    assert res2["passed"] is True
    assert res2["required"] == "4.50m"

    # Band 3: Road width > 18m -> 6.00m
    res3 = check_front_setback(6.0, 24.0, setback_table)
    assert res3["passed"] is True
    assert res3["required"] == "6.00m"


def test_front_setback_exact_boundaries(setback_table):
    """Verify front setback at exact road width boundaries (12m and 18m)."""
    # Just below 12m -> 3.00m
    res_below_12 = check_front_setback(3.0, 11.99, setback_table)
    assert res_below_12["required"] == "3.00m"

    # Exactly 12.00m -> falls in 12m-18m band -> 4.50m
    res_12 = check_front_setback(4.5, 12.0, setback_table)
    assert res_12["required"] == "4.50m"

    # Exactly 18.00m -> falls in 12m-18m band -> 4.50m
    res_18 = check_front_setback(4.5, 18.0, setback_table)
    assert res_18["required"] == "4.50m"

    # Just above 18.00m -> falls in > 18m band -> 6.00m
    res_above_18 = check_front_setback(6.0, 18.01, setback_table)
    assert res_above_18["required"] == "6.00m"


# --- Side & Rear Setback Tests ---

def test_side_and_rear_setback_three_bands(setback_table):
    """Verify side and rear setback requirements across all three plot width bands."""
    # Band 1: Plot width <= 9m -> 1.00m
    s1 = check_side_setback_1(1.0, 8.0, setback_table)
    r1 = check_rear_setback(1.0, 8.0, setback_table)
    assert s1["passed"] is True
    assert s1["rule_id"] == "SETBACK_SIDE1"
    assert s1["required"] == "1.00m"
    assert r1["passed"] is True
    assert r1["rule_id"] == "SETBACK_REAR"
    assert r1["required"] == "1.00m"

    # Band 2: Plot width > 9m to 12m -> 1.50m
    s2 = check_side_setback_1(1.5, 10.5, setback_table)
    r2 = check_rear_setback(1.5, 10.5, setback_table)
    assert s2["required"] == "1.50m"
    assert r2["required"] == "1.50m"

    # Band 3: Plot width > 12m -> 2.00m
    s3 = check_side_setback_1(2.0, 15.0, setback_table)
    r3 = check_rear_setback(2.0, 15.0, setback_table)
    assert s3["required"] == "2.00m"
    assert r3["required"] == "2.00m"


def test_side_and_rear_exact_boundaries(setback_table):
    """Verify side and rear setbacks at exact plot width boundaries (9m and 12m)."""
    # Exactly 9.00m -> falls in <= 9m band -> 1.00m
    s_9 = check_side_setback_1(1.0, 9.0, setback_table)
    assert s_9["required"] == "1.00m"

    # Just above 9.00m -> falls in 9m-12m band -> 1.50m
    s_9_01 = check_side_setback_1(1.5, 9.01, setback_table)
    assert s_9_01["required"] == "1.50m"

    # Exactly 12.00m -> falls in 9m-12m band -> 1.50m
    s_12 = check_side_setback_1(1.5, 12.0, setback_table)
    assert s_12["required"] == "1.50m"

    # Just above 12.00m -> falls in > 12m band -> 2.00m
    s_12_01 = check_side_setback_1(2.0, 12.01, setback_table)
    assert s_12_01["required"] == "2.00m"


# --- Side Setback 2 & Corner Plot Tests ---

def test_side_setback_2_normal_plot(setback_table):
    """Normal plot uses standard side setback for Side 2."""
    # Plot width 10.0m (band 9-12m -> standard 1.50m)
    res_pass = check_side_setback_2(1.5, 10.0, setback_table, is_corner_plot=False)
    assert res_pass["passed"] is True
    assert res_pass["rule_id"] == "SETBACK_SIDE2"
    assert res_pass["required"] == "1.50m"

    res_fail = check_side_setback_2(1.2, 10.0, setback_table, is_corner_plot=False)
    assert res_fail["passed"] is False
    assert res_fail["required"] == "1.50m"


def test_side_setback_2_corner_plot_additional_0_5m(setback_table):
    """Corner plot adds 0.50m to standard side setback for Side 2 (facing second road)."""
    # Plot width 10.0m -> standard 1.50m + 0.50m = 2.00m required
    res_pass = check_side_setback_2(2.0, 10.0, setback_table, is_corner_plot=True)
    assert res_pass["passed"] is True
    assert res_pass["rule_id"] == "SETBACK_SIDE2"
    assert res_pass["required"] == "2.00m"

    res_fail = check_side_setback_2(1.8, 10.0, setback_table, is_corner_plot=True)
    assert res_fail["passed"] is False
    assert res_fail["required"] == "2.00m"
    assert res_fail["proposed"] == "1.80m"


def test_corner_plot_equal_and_unequal_roads(setback_table):
    """Corner plot selects the larger road as front; if equal, either may be front."""
    # Unequal roads: primary 10m, secondary 14m -> front road is 14m -> requires 4.50m
    res_unequal = check_front_setback(
        proposed_front_m=4.5,
        road_width_m=10.0,
        setback_table=setback_table,
        is_corner_plot=True,
        second_road_width_m=14.0,
    )
    assert res_unequal["required"] == "4.50m"

    # Equal roads: primary 9m, secondary 9m -> front road is 9m -> requires 3.00m
    res_equal = check_front_setback(
        proposed_front_m=3.0,
        road_width_m=9.0,
        setback_table=setback_table,
        is_corner_plot=True,
        second_road_width_m=9.0,
    )
    assert res_equal["required"] == "3.00m"


# --- Compounding Classification Tests ---

def test_setback_compounding_classification(setback_table):
    """Deviations <= 0.30m are compoundable; deviations > 0.30m are non-compoundable."""
    # Compliant (0 deviation) -> compoundable is False
    res_ok = check_front_setback(3.0, 10.0, setback_table)
    assert res_ok["passed"] is True
    assert res_ok["compoundable"] is False

    # Shortfall exactly 0.30m (Required 2.00m, proposed 1.70m) -> compoundable is True
    res_comp_03 = check_side_setback_1(1.7, 15.0, setback_table)
    assert res_comp_03["passed"] is False
    assert res_comp_03["compoundable"] is True

    # Shortfall exactly 0.30m with IEEE floating point challenge (Required 1.50m, proposed 1.20m)
    res_comp_03_float = check_side_setback_1(1.2, 10.5, setback_table)
    assert res_comp_03_float["passed"] is False
    assert res_comp_03_float["compoundable"] is True

    # Shortfall 0.20m (<= 0.30m) -> compoundable is True
    res_comp_02 = check_side_setback_1(1.8, 15.0, setback_table)
    assert res_comp_02["passed"] is False
    assert res_comp_02["compoundable"] is True

    # Shortfall 0.31m (> 0.30m) -> compoundable is False
    res_non_comp_031 = check_side_setback_1(1.69, 15.0, setback_table)
    assert res_non_comp_031["passed"] is False
    assert res_non_comp_031["compoundable"] is False

    # Shortfall 0.50m (> 0.30m) -> compoundable is False
    res_non_comp_05 = check_side_setback_1(1.5, 15.0, setback_table)
    assert res_non_comp_05["passed"] is False
    assert res_non_comp_05["compoundable"] is False


# --- Input Validation Tests ---

def test_setback_input_validation(setback_table):
    """Negative setbacks, zero widths, and invalid types are rejected."""
    with pytest.raises(ValueError, match="cannot be negative"):
        check_front_setback(-1.0, 10.0, setback_table)

    with pytest.raises(ValueError, match="must be greater than zero"):
        check_front_setback(3.0, 0.0, setback_table)

    with pytest.raises(TypeError, match="must be a number"):
        check_side_setback_1("2.0", 15.0, setback_table)  # type: ignore

    with pytest.raises(TypeError, match="must be a number"):
        check_side_setback_2(True, 15.0, setback_table)  # type: ignore


# --- Official Planted Test Cases ---

def test_planted_app_0015_front_setback_violation(applications, setback_table):
    """Official scenario: APP-0015 front setback 4.00m on 15m road (needs 4.5m).

    Deviation = 4.50 - 4.00 = 0.50m (> 0.30m) -> Non-compoundable SETBACK_FRONT violation.
    """
    app = next(a for a in applications if a["app_id"] == "APP-0015")
    res = check_front_setback(
        proposed_front_m=app["front_setback_m"],
        road_width_m=app["road_width_m"],
        setback_table=setback_table,
    )
    assert res["passed"] is False
    assert res["rule_id"] == "SETBACK_FRONT"
    assert res["required"] == "4.50m"
    assert res["proposed"] == "4.00m"
    assert res["compoundable"] is False


def test_planted_app_0018_side1_setback_violation(applications, setback_table):
    """Official scenario: APP-0018 side 1 setback 1.20m on 10.5m plot (needs 1.5m).

    Deviation = 1.50 - 1.20 = 0.30m (<= 0.30m) -> Compoundable SETBACK_SIDE1 violation.
    """
    app = next(a for a in applications if a["app_id"] == "APP-0018")
    res = check_side_setback_1(
        proposed_side1_m=app["side_setback_1_m"],
        plot_width_m=app["plot_width_m"],
        setback_table=setback_table,
    )
    assert res["passed"] is False
    assert res["rule_id"] == "SETBACK_SIDE1"
    assert res["required"] == "1.50m"
    assert res["proposed"] == "1.20m"
    assert res["compoundable"] is True


def test_planted_app_0029_rear_setback_violation(applications, setback_table):
    """Official scenario: APP-0029 rear setback 1.50m on 15m plot (needs 2.0m).

    Deviation = 2.00 - 1.50 = 0.50m (> 0.30m) -> Non-compoundable SETBACK_REAR violation.
    """
    app = next(a for a in applications if a["app_id"] == "APP-0029")
    res = check_rear_setback(
        proposed_rear_m=app["rear_setback_m"],
        plot_width_m=app["plot_width_m"],
        setback_table=setback_table,
    )
    assert res["passed"] is False
    assert res["rule_id"] == "SETBACK_REAR"
    assert res["required"] == "2.00m"
    assert res["proposed"] == "1.50m"
    assert res["compoundable"] is False


def test_planted_app_0020_corner_side2_violation(applications, setback_table):
    """Official scenario: APP-0020 corner plot: second-road side 2.20m (needs 2.0 + 0.5 = 2.5m).

    Deviation = 2.50 - 2.20 = 0.30m (<= 0.30m) -> Compoundable SETBACK_SIDE2 violation.
    """
    app = next(a for a in applications if a["app_id"] == "APP-0020")
    res = check_side_setback_2(
        proposed_side2_m=app["side_setback_2_m"],
        plot_width_m=app["plot_width_m"],
        setback_table=setback_table,
        is_corner_plot=app["is_corner_plot"],
    )
    assert res["passed"] is False
    assert res["rule_id"] == "SETBACK_SIDE2"
    assert res["required"] == "2.50m"
    assert res["proposed"] == "2.20m"
    assert res["compoundable"] is True


def test_planted_app_0024_equal_road_corner_all_setbacks_pass(applications, setback_table):
    """Official scenario: APP-0024 corner plot on two 9.00m roads.

    Either road is front (3.00m); side 2 needs 2.00 + 0.50 = 2.50m.
    Proposed: Front 3.5m >= 3.0m, Side 1 2.0m >= 2.0m, Side 2 3.0m >= 2.5m, Rear 2.5m >= 2.0m.
    All setbacks pass!
    """
    app = next(a for a in applications if a["app_id"] == "APP-0024")
    all_res = check_all_setbacks(app, setback_table)

    assert len(all_res) == 4
    for r in all_res:
        assert r["passed"] is True
        assert r["compoundable"] is False

    rule_ids = [r["rule_id"] for r in all_res]
    assert rule_ids == ["SETBACK_FRONT", "SETBACK_SIDE1", "SETBACK_SIDE2", "SETBACK_REAR"]

