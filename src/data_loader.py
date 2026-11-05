"""Data Loader Module for Municipal Plan Approval Engine.

Responsible for:
1. Loading official CSV tables using Python's built-in `csv` module.
2. Careful parsing of numeric types, booleans, and semicolon-delimited sets.
3. Interval lookup utility respecting inclusive and exclusive boundary flags.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path


# ==============================================================================
# Helper Type Parsers
# ==============================================================================

def parse_bool(val: str | bool) -> bool:
    """Parse string or boolean into a strict boolean.

    'true' (case-insensitive) -> True
    'false' (case-insensitive) -> False
    """
    if isinstance(val, bool):
        return val
    cleaned = str(val).strip().lower()
    if cleaned == "true":
        return True
    if cleaned == "false":
        return False
    raise ValueError(f"Invalid boolean string: {val!r}")


def parse_float(val: str | float | None, default: float | None = None) -> float | None:
    """Parse string to float, returning default if empty."""
    if val is None:
        return default
    cleaned = str(val).strip()
    if not cleaned or cleaned == "-":
        return default
    return float(cleaned)


def parse_int(val: str | int | None, default: int | None = None) -> int | None:
    """Parse string to integer, returning default if empty."""
    if val is None:
        return default
    cleaned = str(val).strip()
    if not cleaned or cleaned == "-":
        return default
    return int(cleaned)


# ==============================================================================
# Interval Matching Utility
# ==============================================================================

def check_interval(
    value: float,
    from_val: float,
    from_inclusive: bool,
    to_val: float,
    to_inclusive: bool,
) -> bool:
    """Check if value falls within [from_val, to_val] respecting boundary inclusivity.

    Args:
        value: The numeric value being checked (e.g., road width or plot area).
        from_val: Lower bound of the interval.
        from_inclusive: If True, value >= from_val; if False, value > from_val.
        to_val: Upper bound of the interval.
        to_inclusive: If True, value <= to_val; if False, value < to_val.

    Returns:
        bool: True if value satisfies both lower and upper boundary conditions.
    """
    lower_ok = (value >= from_val) if from_inclusive else (value > from_val)
    upper_ok = (value <= to_val) if to_inclusive else (value < to_val)
    return lower_ok and upper_ok


# ==============================================================================
# CSV Table Loaders
# ==============================================================================

def load_zones(file_path: str | Path) -> dict[str, dict]:
    """Load zones.csv into a dictionary keyed by zone_id."""
    zones = {}
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zone_id = row["zone_id"].strip()
            permitted_list = [u.strip() for u in row["permitted_uses"].split(";") if u.strip()]
            zones[zone_id] = {
                "zone_id": zone_id,
                "zone_name": row["zone_name"].strip(),
                "zone_category": row["zone_category"].strip().upper(),
                "permitted_uses": set(permitted_list),
                "height_cap_road_lt_12_m": float(row["height_cap_road_lt_12_m"]),
                "height_cap_road_ge_12_m": float(row["height_cap_road_ge_12_m"]),
            }
    return zones


def load_far_table(file_path: str | Path) -> list[dict]:
    """Load far_table.csv into a list of parsed interval dictionaries."""
    rows = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "zone_id": row["zone_id"].strip(),
                "road_width_from_m": float(row["road_width_from_m"]),
                "from_inclusive": parse_bool(row["from_inclusive"]),
                "road_width_to_m": float(row["road_width_to_m"]),
                "to_inclusive": parse_bool(row["to_inclusive"]),
                "base_far": float(row["base_far"]),
            })
    return rows


def load_setback_table(file_path: str | Path) -> list[dict]:
    """Load setback_table.csv into a list of parsed interval dictionaries."""
    rows = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "setback_type": row["setback_type"].strip().upper(),
                "measure": row["measure"].strip().upper(),
                "from_m": float(row["from_m"]),
                "from_inclusive": parse_bool(row["from_inclusive"]),
                "to_m": float(row["to_m"]),
                "to_inclusive": parse_bool(row["to_inclusive"]),
                "setback_m": float(row["setback_m"]),
            })
    return rows


def load_coverage_table(file_path: str | Path) -> list[dict]:
    """Load coverage_table.csv into a list of parsed interval dictionaries."""
    rows = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "plot_area_from_sqm": float(row["plot_area_from_sqm"]),
                "from_inclusive": parse_bool(row["from_inclusive"]),
                "plot_area_to_sqm": float(row["plot_area_to_sqm"]),
                "to_inclusive": parse_bool(row["to_inclusive"]),
                "max_coverage_pct": float(row["max_coverage_pct"]),
            })
    return rows


def load_fee_schedule(file_path: str | Path) -> dict[str, dict]:
    """Load fee_schedule.csv into a dictionary keyed by fee_code."""
    fees = {}
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["fee_code"].strip()
            fees[code] = {
                "fee_code": code,
                "rate": float(row["rate"]),
                "unit": row["unit"].strip(),
                "notes": row["notes"].strip(),
            }
    return fees


def load_holidays(file_path: str | Path) -> set[str]:
    """Load holidays.csv into a set of 'YYYY-MM-DD' date strings."""
    holidays = set()
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row["holiday_date"].strip()
            if date_str:
                holidays.add(date_str)
    return holidays


def load_applications(file_path: str | Path) -> list[dict]:
    """Load applications.csv into a list of parsed application dictionaries."""
    apps = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            apps.append({
                "app_id": row["app_id"].strip(),
                "applicant_name": row["applicant_name"].strip(),
                "survey_no": row["survey_no"].strip(),
                "zone_id": row["zone_id"].strip(),
                "proposed_use": row["proposed_use"].strip().upper(),
                "plot_width_m": float(row["plot_width_m"]),
                "plot_depth_m": float(row["plot_depth_m"]),
                "plot_area_sqm": float(row["plot_area_sqm"]),
                "road_width_m": float(row["road_width_m"]),
                "is_corner_plot": parse_bool(row["is_corner_plot"]),
                "second_road_width_m": parse_float(row.get("second_road_width_m")),
                "front_setback_m": float(row["front_setback_m"]),
                "side_setback_1_m": float(row["side_setback_1_m"]),
                "side_setback_2_m": float(row["side_setback_2_m"]),
                "rear_setback_m": float(row["rear_setback_m"]),
                "ground_footprint_sqm": float(row["ground_footprint_sqm"]),
                "building_height_m": float(row["building_height_m"]),
                "premium_far_requested": float(row["premium_far_requested"]),
                "tdr_far_requested": float(row["tdr_far_requested"]),
                "units_carpet_above_100": int(row["units_carpet_above_100"]),
                "units_carpet_upto_100": int(row["units_carpet_upto_100"]),
                "parking_proposed": int(row["parking_proposed"]),
                "agri_converted": parse_bool(row["agri_converted"]),
                "guidance_value_per_sqm": float(row["guidance_value_per_sqm"]),
                "submitted_date": row["submitted_date"].strip(),
            })
    return apps


def load_floors(file_path: str | Path) -> dict[str, list[dict]]:
    """Load floors.csv into a dictionary mapping app_id -> list of floor dicts."""
    floors_by_app: dict[str, list[dict]] = {}
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            app_id = row["app_id"].strip()
            item = {
                "app_id": app_id,
                "floor_no": row["floor_no"].strip(),
                "floor_use": row["floor_use"].strip().upper(),
                "built_up_sqm": float(row["built_up_sqm"]),
                "balcony_sqm": float(row["balcony_sqm"]),
            }
            floors_by_app.setdefault(app_id, []).append(item)
    return floors_by_app


# ==============================================================================
# Master Loader & Interval Query Helpers
# ==============================================================================

def load_data_pack(data_dir: str | Path) -> dict:
    """Load all municipal dataset files from the given data directory."""
    d = Path(data_dir)
    return {
        "zones": load_zones(d / "zones.csv"),
        "far_table": load_far_table(d / "far_table.csv"),
        "setback_table": load_setback_table(d / "setback_table.csv"),
        "coverage_table": load_coverage_table(d / "coverage_table.csv"),
        "fee_schedule": load_fee_schedule(d / "fee_schedule.csv"),
        "holidays": load_holidays(d / "holidays.csv"),
        "applications": load_applications(d / "applications.csv"),
        "floors_by_app": load_floors(d / "floors.csv"),
    }


def lookup_base_far(far_rows: list[dict], zone_id: str, road_width: float) -> float:
    """Lookup base FAR from far_table rows matching zone and road width interval."""
    for row in far_rows:
        if row["zone_id"] == zone_id and check_interval(
            road_width,
            row["road_width_from_m"],
            row["from_inclusive"],
            row["road_width_to_m"],
            row["to_inclusive"],
        ):
            return row["base_far"]
    raise ValueError(f"No base FAR rule found for zone {zone_id!r} with road width {road_width}m.")


def lookup_setback(setback_rows: list[dict], setback_type: str, measure_val: float) -> float:
    """Lookup required setback (FRONT or SIDE_REAR) from setback_table rows."""
    stype = setback_type.strip().upper()
    for row in setback_rows:
        if row["setback_type"] == stype and check_interval(
            measure_val,
            row["from_m"],
            row["from_inclusive"],
            row["to_m"],
            row["to_inclusive"],
        ):
            return row["setback_m"]
    raise ValueError(f"No setback rule found for {stype} with measure {measure_val}m.")


def lookup_max_coverage(coverage_rows: list[dict], plot_area: float) -> float:
    """Lookup max ground coverage percentage from coverage_table rows."""
    for row in coverage_rows:
        if check_interval(
            plot_area,
            row["plot_area_from_sqm"],
            row["from_inclusive"],
            row["plot_area_to_sqm"],
            row["to_inclusive"],
        ):
            return row["max_coverage_pct"]
    raise ValueError(f"No coverage rule found for plot area {plot_area} sq.m.")

