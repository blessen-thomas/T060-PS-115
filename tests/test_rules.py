"""Unit Tests for Municipal Rule Validation Engine (src/rules.py)."""

from pathlib import Path
import pytest

from src.data_loader import load_applications, load_coverage_table, load_zones
from src.rules import check_ground_coverage, check_zoning_use

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

