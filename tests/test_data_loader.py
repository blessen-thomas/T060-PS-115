"""Tests for CSV Data Loader and Interval Lookup Utilities."""

from pathlib import Path
import pytest

from src.data_loader import (
    check_interval,
    load_applications,
    load_coverage_table,
    load_data_pack,
    load_far_table,
    load_fee_schedule,
    load_floors,
    load_holidays,
    load_setback_table,
    load_zones,
    lookup_base_far,
    lookup_max_coverage,
    lookup_setback,
    parse_bool,
    parse_float,
    parse_int,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ==============================================================================
# 1. Type Parser Tests
# ==============================================================================

def test_parse_bool():
    """Verify boolean parsing handles case-insensitivity and strict rejection."""
    assert parse_bool("true") is True
    assert parse_bool("True") is True
    assert parse_bool("TRUE") is True
    assert parse_bool(True) is True

    assert parse_bool("false") is False
    assert parse_bool("False") is False
    assert parse_bool("FALSE") is False
    assert parse_bool(False) is False

    with pytest.raises(ValueError, match="Invalid boolean string"):
        parse_bool("yes")

    with pytest.raises(ValueError, match="Invalid boolean string"):
        parse_bool("1")


def test_parse_numeric_helpers():
    """Verify float and int parsing with blanks and dashes."""
    assert parse_float("12.5") == 12.5
    assert parse_float("", default=0.0) == 0.0
    assert parse_float("-", default=None) is None
    assert parse_float(None, default=5.0) == 5.0

    assert parse_int("42") == 42
    assert parse_int("", default=0) == 0
    assert parse_int("-", default=None) is None
    assert parse_int(None, default=10) == 10


# ==============================================================================
# 2. Interval Lookup Boundary Tests
# ==============================================================================

def test_check_interval_inclusive_both():
    """Test [10.0, 20.0] inclusive on both ends."""
    assert check_interval(10.0, 10.0, True, 20.0, True) is True
    assert check_interval(15.0, 10.0, True, 20.0, True) is True
    assert check_interval(20.0, 10.0, True, 20.0, True) is True
    assert check_interval(9.99, 10.0, True, 20.0, True) is False
    assert check_interval(20.01, 10.0, True, 20.0, True) is False


def test_check_interval_exclusive_bounds():
    """Test (10.0, 20.0) exclusive on both ends."""
    assert check_interval(10.0, 10.0, False, 20.0, False) is False
    assert check_interval(10.01, 10.0, False, 20.0, False) is True
    assert check_interval(19.99, 10.0, False, 20.0, False) is True
    assert check_interval(20.0, 10.0, False, 20.0, False) is False


def test_check_interval_mixed_bounds():
    """Test [10.0, 20.0) inclusive lower, exclusive upper."""
    assert check_interval(10.0, 10.0, True, 20.0, False) is True
    assert check_interval(19.99, 10.0, True, 20.0, False) is True
    assert check_interval(20.0, 10.0, True, 20.0, False) is False


# ==============================================================================
# 3. Official CSV File Loading Tests
# ==============================================================================

def test_load_zones():
    """Verify loading of zones.csv."""
    zones = load_zones(DATA_DIR / "zones.csv")
    assert len(zones) == 4
    assert "ZN-R1" in zones
    assert "ZN-C1" in zones

    zn_r1 = zones["ZN-R1"]
    assert zn_r1["zone_category"] == "RESIDENTIAL"
    assert zn_r1["permitted_uses"] == {"RESIDENTIAL"}
    assert zn_r1["height_cap_road_lt_12_m"] == 15.0
    assert zn_r1["height_cap_road_ge_12_m"] == 24.0

    zn_mx = zones["ZN-MX"]
    assert zn_mx["permitted_uses"] == {"RESIDENTIAL", "COMMERCIAL", "MIXED"}


def test_load_far_table():
    """Verify loading of far_table.csv."""
    far_table = load_far_table(DATA_DIR / "far_table.csv")
    assert len(far_table) == 12
    first = far_table[0]
    assert first["zone_id"] == "ZN-R1"
    assert first["road_width_from_m"] == 0.0
    assert first["from_inclusive"] is True
    assert first["road_width_to_m"] == 12.0
    assert first["to_inclusive"] is False
    assert first["base_far"] == 1.75


def test_load_setback_table():
    """Verify loading of setback_table.csv."""
    setback_table = load_setback_table(DATA_DIR / "setback_table.csv")
    assert len(setback_table) == 6
    front_rules = [r for r in setback_table if r["setback_type"] == "FRONT"]
    assert len(front_rules) == 3


def test_load_coverage_table():
    """Verify loading of coverage_table.csv."""
    coverage_table = load_coverage_table(DATA_DIR / "coverage_table.csv")
    assert len(coverage_table) == 3
    assert coverage_table[0]["max_coverage_pct"] == 65.0
    assert coverage_table[1]["max_coverage_pct"] == 60.0
    assert coverage_table[2]["max_coverage_pct"] == 50.0


def test_load_fee_schedule():
    """Verify loading of fee_schedule.csv."""
    fees = load_fee_schedule(DATA_DIR / "fee_schedule.csv")
    assert len(fees) == 14
    assert fees["SCRUTINY"]["rate"] == 20.0
    assert fees["PREMIUM_FAR_RES"]["rate"] == 40.0
    assert fees["PREMIUM_FAR_COM"]["rate"] == 60.0


def test_load_holidays():
    """Verify loading of holidays.csv."""
    holidays = load_holidays(DATA_DIR / "holidays.csv")
    assert len(holidays) == 12
    assert "2026-01-26" in holidays


def test_load_applications():
    """Verify loading of applications.csv."""
    apps = load_applications(DATA_DIR / "applications.csv")
    assert len(apps) == 40

    app1 = apps[0]
    assert app1["app_id"] == "APP-0001"
    assert app1["is_corner_plot"] is False
    assert app1["second_road_width_m"] is None

    # Check a corner plot (APP-0020)
    app20 = next(a for a in apps if a["app_id"] == "APP-0020")
    assert app20["is_corner_plot"] is True
    assert app20["second_road_width_m"] == 7.50


def test_load_floors():
    """Verify loading of floors.csv."""
    floors_by_app = load_floors(DATA_DIR / "floors.csv")
    assert len(floors_by_app) == 40
    assert "APP-0001" in floors_by_app
    app1_floors = floors_by_app["APP-0001"]
    assert len(app1_floors) == 7
    assert app1_floors[0]["floor_no"] == "G"
    assert app1_floors[0]["floor_use"] == "PARKING"


def test_load_data_pack():
    """Verify master loader loads all data sets consistently."""
    pack = load_data_pack(DATA_DIR)
    assert len(pack["zones"]) == 4
    assert len(pack["far_table"]) == 12
    assert len(pack["setback_table"]) == 6
    assert len(pack["coverage_table"]) == 3
    assert len(pack["applications"]) == 40
    assert len(pack["floors_by_app"]) == 40


# ==============================================================================
# 4. Table-Based Lookup Query Tests with Exact Boundaries
# ==============================================================================

def test_lookup_base_far_boundaries():
    """Verify exact boundary values for base FAR lookup in ZN-R1."""
    far_table = load_far_table(DATA_DIR / "far_table.csv")

    # Band 1: [0.0, 12.0)
    assert lookup_base_far(far_table, "ZN-R1", 0.0) == 1.75
    assert lookup_base_far(far_table, "ZN-R1", 11.99) == 1.75

    # Band 2: [12.0, 18.0] - both edges inclusive
    assert lookup_base_far(far_table, "ZN-R1", 12.0) == 2.25
    assert lookup_base_far(far_table, "ZN-R1", 15.0) == 2.25
    assert lookup_base_far(far_table, "ZN-R1", 18.0) == 2.25

    # Band 3: (18.0, 99.0] - lower exclusive
    assert lookup_base_far(far_table, "ZN-R1", 18.01) == 2.50
    assert lookup_base_far(far_table, "ZN-R1", 24.0) == 2.50

    # Unknown zone raises ValueError
    with pytest.raises(ValueError, match="No base FAR rule found"):
        lookup_base_far(far_table, "ZN-UNKNOWN", 12.0)


def test_lookup_max_coverage_boundaries():
    """Verify exact boundary values for ground coverage table."""
    coverage_table = load_coverage_table(DATA_DIR / "coverage_table.csv")

    # Band 1: [0.0, 200.0] -> 65%
    assert lookup_max_coverage(coverage_table, 100.0) == 65.0
    assert lookup_max_coverage(coverage_table, 200.0) == 65.0

    # Band 2: (200.0, 500.0] -> 60%
    assert lookup_max_coverage(coverage_table, 200.01) == 60.0
    assert lookup_max_coverage(coverage_table, 350.0) == 60.0
    assert lookup_max_coverage(coverage_table, 500.0) == 60.0

    # Band 3: (500.0, 999999.0] -> 50%
    assert lookup_max_coverage(coverage_table, 500.01) == 50.0
    assert lookup_max_coverage(coverage_table, 1000.0) == 50.0


def test_lookup_setback_boundaries():
    """Verify exact boundary values for setbacks table."""
    setback_table = load_setback_table(DATA_DIR / "setback_table.csv")

    # FRONT setback by road width: [0, 12) -> 3.0m; [12, 18] -> 4.5m; (18, 99] -> 6.0m
    assert lookup_setback(setback_table, "FRONT", 9.0) == 3.0
    assert lookup_setback(setback_table, "FRONT", 11.99) == 3.0
    assert lookup_setback(setback_table, "FRONT", 12.0) == 4.5
    assert lookup_setback(setback_table, "FRONT", 18.0) == 4.5
    assert lookup_setback(setback_table, "FRONT", 18.01) == 6.0

    # SIDE_REAR setback by plot width: [0, 9] -> 1.0m; (9, 12] -> 1.5m; (12, 999] -> 2.0m
    assert lookup_setback(setback_table, "SIDE_REAR", 8.0) == 1.0
    assert lookup_setback(setback_table, "SIDE_REAR", 9.0) == 1.0
    assert lookup_setback(setback_table, "SIDE_REAR", 9.01) == 1.5
    assert lookup_setback(setback_table, "SIDE_REAR", 12.0) == 1.5
    assert lookup_setback(setback_table, "SIDE_REAR", 12.01) == 2.0

