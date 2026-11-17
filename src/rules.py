"""Municipal Building Plan Approval Rule Checkers.

Each rule function performs a dedicated validation check and returns
a standardized dictionary matching the official validation report format:
- passed: bool (True if compliant, False if violation)
- rule_id: str (Official rule code)
- check: str (Human-readable description of the check)
- required: str (Required threshold or permitted specification)
- proposed: str (Proposed value or specification from application)
- compoundable: bool (Whether the violation can be regularized via compounding fees)
"""

from __future__ import annotations

import math

from src.data_loader import lookup_max_coverage, lookup_setback
from src.far import get_base_far


def _validate_numeric(val: any, field_name: str, allow_zero: bool = True) -> float:
    """Validate that value is a real number and conforms to positivity constraints."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TypeError(f"{field_name} must be a number (int or float).")
    num = float(val)
    if allow_zero:
        if num < 0:
            raise ValueError(f"{field_name} cannot be negative.")
    else:
        if num <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")
    return num


def check_zoning_use(
    zone_id: str,
    proposed_use: str,
    zones: dict[str, dict],
    raise_on_unknown_zone: bool = False,
) -> dict:
    """Validate whether the proposed building use is permitted in the designated zone.

    Rule ID:
        ZONING_USE

    Precedence:
        1 (First in municipal evaluation precedence)

    Args:
        zone_id: Municipal zone identifier (e.g., 'ZN-R1', 'ZN-C1').
        proposed_use: Proposed use category ('RESIDENTIAL', 'COMMERCIAL', 'MIXED').
        zones: Dictionary of loaded zone records keyed by zone_id.
        raise_on_unknown_zone: If True, raises ValueError on unknown zone_id.
                               If False, returns a failed validation result safely.

    Returns:
        dict: Standard validation result dictionary.

    Raises:
        ValueError: If zone_id is not recognized and raise_on_unknown_zone is True.
    """
    clean_zone = zone_id.strip() if isinstance(zone_id, str) else str(zone_id)
    clean_use = proposed_use.strip().upper() if isinstance(proposed_use, str) else str(proposed_use)

    if clean_zone not in zones:
        if raise_on_unknown_zone:
            raise ValueError(
                f"Unknown zone_id: {clean_zone!r}. "
                f"Available zones are: {list(zones.keys())}"
            )
        return {
            "passed": False,
            "rule_id": "ZONING_USE",
            "check": f"Permitted building use in zone {clean_zone}",
            "required": "VALID_ZONE",
            "proposed": f"Unknown zone: {clean_zone}",
            "compoundable": False,
        }

    zone_info = zones[clean_zone]
    permitted_uses: set[str] = zone_info["permitted_uses"]

    is_permitted = clean_use in permitted_uses
    required_display = ";".join(sorted(permitted_uses))

    return {
        "passed": is_permitted,
        "rule_id": "ZONING_USE",
        "check": f"Permitted building use in zone {clean_zone}",
        "required": required_display,
        "proposed": clean_use,
        "compoundable": False,
    }


# ==============================================================================
# Floor Area Ratio (FAR) Statutory Validation Checkers (Precedence 2)
# ==============================================================================

def check_premium_far(
    premium_far_requested: float,
    road_width_m: float,
) -> dict:
    """Validate requested premium FAR against road width and statutory limits.

    Rule ID:
        FAR_PREMIUM

    Precedence:
        Follows FAR_BASE in municipal evaluation precedence.

    Rules:
        - Premium FAR requires abutting road width >= 12.0m.
        - Premium FAR cannot exceed 0.50.

    Args:
        premium_far_requested: Additional premium FAR requested.
        road_width_m: Abutting road width in metres.

    Returns:
        dict: Standard validation report dictionary.
    """
    prem_req = _validate_numeric(premium_far_requested, "premium_far_requested", allow_zero=True)
    width = _validate_numeric(road_width_m, "road_width_m", allow_zero=False)

    if prem_req <= 0.0:
        return {
            "passed": True,
            "rule_id": "FAR_PREMIUM",
            "check": "Premium FAR limit (max 0.50)",
            "required": "<= 0.50",
            "proposed": f"{prem_req:.2f}",
            "compoundable": False,
        }

    if width < 12.0:
        return {
            "passed": False,
            "rule_id": "FAR_PREMIUM",
            "check": "Premium FAR road width requirement (>= 12.0m)",
            "required": ">= 12.00m",
            "proposed": f"{width:.2f}m",
            "compoundable": False,
        }

    if prem_req > 0.50:
        return {
            "passed": False,
            "rule_id": "FAR_PREMIUM",
            "check": "Premium FAR limit (max 0.50)",
            "required": "<= 0.50",
            "proposed": f"{prem_req:.2f}",
            "compoundable": False,
        }

    return {
        "passed": True,
        "rule_id": "FAR_PREMIUM",
        "check": "Premium FAR limit (max 0.50)",
        "required": "<= 0.50",
        "proposed": f"{prem_req:.2f}",
        "compoundable": False,
    }


def check_tdr_far(tdr_far_requested: float) -> dict:
    """Validate requested TDR FAR against statutory maximum limit (0.40).

    Rule ID:
        FAR_TDR

    Precedence:
        Follows FAR_PREMIUM in municipal evaluation precedence.

    Args:
        tdr_far_requested: Additional TDR FAR requested.

    Returns:
        dict: Standard validation report dictionary.
    """
    tdr_req = _validate_numeric(tdr_far_requested, "tdr_far_requested", allow_zero=True)
    passed = tdr_req <= 0.40
    return {
        "passed": passed,
        "rule_id": "FAR_TDR",
        "check": "TDR FAR limit (max 0.40)",
        "required": "<= 0.40",
        "proposed": f"{tdr_req:.2f}",
        "compoundable": False,
    }


def check_combined_far_cap(
    premium_far_requested: float,
    tdr_far_requested: float,
) -> dict:
    """Validate combined additional FAR (Premium + TDR) against statutory cap of 0.60.

    Rule ID:
        FAR_CAP

    Precedence:
        Follows FAR_TDR in municipal evaluation precedence.

    Args:
        premium_far_requested: Additional premium FAR requested.
        tdr_far_requested: Additional TDR FAR requested.

    Returns:
        dict: Standard validation report dictionary.
    """
    prem_req = _validate_numeric(premium_far_requested, "premium_far_requested", allow_zero=True)
    tdr_req = _validate_numeric(tdr_far_requested, "tdr_far_requested", allow_zero=True)
    combined = prem_req + tdr_req
    passed = combined <= 0.60
    return {
        "passed": passed,
        "rule_id": "FAR_CAP",
        "check": "Combined additional FAR cap (Premium + TDR <= 0.60)",
        "required": "<= 0.60",
        "proposed": f"{combined:.2f}",
        "compoundable": False,
    }


def check_far_achieved(
    plot_area_sqm: float,
    eligible_built_up_area: float,
    allowed_far: float,
    road_width_m: float,
) -> dict:
    """Validate whether the proposed built-up area complies with total permitted FAR.

    Rule ID:
        FAR_ACHIEVED

    Precedence:
        Follows FAR_CAP in municipal evaluation precedence.

    Args:
        plot_area_sqm: Site/plot area in sq.m.
        eligible_built_up_area: Eligible built-up area after exclusions.
        allowed_far: Total permitted FAR (Base + allowed additional).
        road_width_m: Abutting road width in metres.

    Returns:
        dict: Standard validation report dictionary.
    """
    plot_area = _validate_numeric(plot_area_sqm, "plot_area_sqm", allow_zero=False)
    eligible_bua = _validate_numeric(eligible_built_up_area, "eligible_built_up_area", allow_zero=True)
    allowed = _validate_numeric(allowed_far, "allowed_far", allow_zero=False)
    width = _validate_numeric(road_width_m, "road_width_m", allow_zero=False)

    far_achieved = eligible_bua / plot_area
    passed = far_achieved <= allowed

    return {
        "passed": passed,
        "rule_id": "FAR_ACHIEVED",
        "check": f"Permitted FAR for road {width:.2f}m",
        "required": f"{allowed:.2f}",
        "proposed": f"{far_achieved:.4f}",
        "compoundable": False,
    }


def check_all_far_rules(
    plot_area_sqm: float,
    road_width_m: float,
    proposed_use: str,
    eligible_built_up_area: float,
    premium_far_requested: float = 0.0,
    tdr_far_requested: float = 0.0,
) -> list[dict]:
    """Validate all statutory FAR rules in precedence order:
    1. FAR_PREMIUM (if premium FAR requested)
    2. FAR_TDR (if TDR FAR requested)
    3. FAR_CAP (if additional FAR requested)
    4. FAR_ACHIEVED (always evaluated)

    Args:
        plot_area_sqm: Plot area in square metres.
        road_width_m: Abutting road width in metres.
        proposed_use: Use category ('RESIDENTIAL', 'COMMERCIAL', 'MIXED').
        eligible_built_up_area: Eligible built-up area after deductions.
        premium_far_requested: Additional premium FAR requested.
        tdr_far_requested: Additional TDR FAR requested.

    Returns:
        list[dict]: List of rule check result dictionaries.
    """
    use_for_far = "mixed_use" if str(proposed_use).strip().lower() in ("mixed", "mixed_use") else str(proposed_use).strip().lower()
    base_far = get_base_far(use_for_far, float(road_width_m))

    prem_req = float(premium_far_requested or 0.0)
    tdr_req = float(tdr_far_requested or 0.0)
    road_width = float(road_width_m)
    plot_area = float(plot_area_sqm)
    eligible_bua = float(eligible_built_up_area)

    checks: list[dict] = []

    if prem_req > 0.0:
        checks.append(check_premium_far(prem_req, road_width))

    if tdr_req > 0.0:
        checks.append(check_tdr_far(tdr_req))

    if prem_req > 0.0 or tdr_req > 0.0:
        checks.append(check_combined_far_cap(prem_req, tdr_req))

    allowed_additional = min(0.60, prem_req + tdr_req) if road_width >= 12.0 or prem_req == 0.0 else min(0.60, tdr_req)
    total_allowed_far = base_far + allowed_additional

    checks.append(check_far_achieved(
        plot_area_sqm=plot_area,
        eligible_built_up_area=eligible_bua,
        allowed_far=total_allowed_far,
        road_width_m=road_width,
    ))

    return checks


def check_ground_coverage(
    ground_footprint_sqm: float,
    plot_area_sqm: float,
    coverage_table: list[dict],
) -> dict:
    """Validate whether the proposed ground footprint complies with maximum coverage limits.

    Formula:
        Coverage Percentage = (ground_footprint_sqm / plot_area_sqm) * 100

    Rule ID:
        GROUND_COVERAGE

    Precedence:
        Follows FAR in municipal evaluation precedence.

    Args:
        ground_footprint_sqm: Building footprint on ground (including stilt parking).
        plot_area_sqm: Total area of the site/plot.
        coverage_table: List of coverage table interval dictionaries from coverage_table.csv.

    Returns:
        dict: Standard validation report dictionary:
            - passed: bool (True if actual coverage <= max permitted coverage)
            - rule_id: 'GROUND_COVERAGE'
            - check: Description of the coverage check
            - required: Max allowed percentage string (e.g. '60.00%')
            - proposed: Actual proposed percentage string (e.g. '61.11%')
            - compoundable: False (ground coverage violations cannot be compounded)

    Raises:
        TypeError: If ground_footprint_sqm or plot_area_sqm is not numeric.
        ValueError: If plot_area_sqm <= 0 or ground_footprint_sqm < 0.
    """
    if isinstance(plot_area_sqm, bool) or not isinstance(plot_area_sqm, (int, float)):
        raise TypeError("Plot area must be a number (int or float).")
    if isinstance(ground_footprint_sqm, bool) or not isinstance(ground_footprint_sqm, (int, float)):
        raise TypeError("Ground footprint area must be a number (int or float).")

    plot_num = float(plot_area_sqm)
    footprint_num = float(ground_footprint_sqm)

    if plot_num <= 0:
        raise ValueError("Plot area must be greater than zero.")
    if footprint_num < 0:
        raise ValueError("Ground footprint area cannot be negative.")

    max_coverage_pct = lookup_max_coverage(coverage_table, plot_num)

    # Calculate actual percentage without premature rounding
    actual_coverage_pct = (footprint_num / plot_num) * 100.0
    passed = actual_coverage_pct <= max_coverage_pct

    return {
        "passed": passed,
        "rule_id": "GROUND_COVERAGE",
        "check": f"Ground coverage limit for plot area {plot_num:.2f} sq.m",
        "required": f"{max_coverage_pct:.2f}%",
        "proposed": f"{actual_coverage_pct:.2f}%",
        "compoundable": False,
    }


# ==============================================================================
# Helper Functions for Setback Validation
# ==============================================================================

def _evaluate_setback(
    rule_id: str,
    check_description: str,
    required_m: float,
    proposed_m: float,
) -> dict:
    """Evaluate setback compliance and compounding eligibility.

    Rules:
        - passed: True if proposed >= required, else False.
        - compoundable: True if deviation <= 0.30m (30 cm shortfall), else False.
        - If passed, compoundable is False (no violation).
    """
    # Round deviation to 4 decimal places to prevent IEEE 754 precision issues (e.g. 1.5 - 1.2 = 0.30000000000000004)
    deviation = round(required_m - proposed_m, 4)
    passed = deviation <= 0.0
    compoundable = (not passed) and (deviation <= 0.30)

    return {
        "passed": passed,
        "rule_id": rule_id,
        "check": check_description,
        "required": f"{required_m:.2f}m",
        "proposed": f"{proposed_m:.2f}m",
        "compoundable": compoundable,
    }


# ==============================================================================
# Setback Validation Rules
# ==============================================================================

def check_front_setback(
    proposed_front_m: float,
    road_width_m: float,
    setback_table: list[dict],
    is_corner_plot: bool = False,
    second_road_width_m: float | None = None,
) -> dict:
    """Validate proposed front setback against municipal road-width requirements.

    Rule ID:
        SETBACK_FRONT

    Road Width Bands:
        - Below 12m: 3.00m
        - 12m to 18m inclusive: 4.50m
        - Above 18m: 6.00m

    Corner Plot Rule:
        The larger road is treated as the front road.
        If both roads are equal in width, either may be treated as the front road.

    Args:
        proposed_front_m: Proposed front open space in metres.
        road_width_m: Primary abutting road width in metres.
        setback_table: Parsed rows from setback_table.csv.
        is_corner_plot: Whether the plot is situated at a road junction.
        second_road_width_m: Optional width of the secondary abutting road in metres.

    Returns:
        dict: Standard validation report dictionary.
    """
    prop = _validate_numeric(proposed_front_m, "Proposed front setback", allow_zero=True)
    rw1 = _validate_numeric(road_width_m, "Road width", allow_zero=False)

    effective_road_w = rw1
    if is_corner_plot and second_road_width_m is not None:
        rw2 = _validate_numeric(second_road_width_m, "Second road width", allow_zero=False)
        effective_road_w = max(rw1, rw2)

    required_m = lookup_setback(setback_table, "FRONT", effective_road_w)
    return _evaluate_setback(
        rule_id="SETBACK_FRONT",
        check_description=f"Front setback for road width {effective_road_w:.2f}m",
        required_m=required_m,
        proposed_m=prop,
    )


def check_side_setback_1(
    proposed_side1_m: float,
    plot_width_m: float,
    setback_table: list[dict],
) -> dict:
    """Validate proposed side setback 1 against plot-width requirements.

    Rule ID:
        SETBACK_SIDE1

    Plot Width Bands:
        - Up to 9m inclusive: 1.00m
        - Above 9m to 12m inclusive: 1.50m
        - Above 12m: 2.00m

    Args:
        proposed_side1_m: Proposed side 1 open space in metres.
        plot_width_m: Frontage / plot width in metres.
        setback_table: Parsed rows from setback_table.csv.

    Returns:
        dict: Standard validation report dictionary.
    """
    prop = _validate_numeric(proposed_side1_m, "Proposed side setback 1", allow_zero=True)
    pw = _validate_numeric(plot_width_m, "Plot width", allow_zero=False)

    required_m = lookup_setback(setback_table, "SIDE_REAR", pw)
    return _evaluate_setback(
        rule_id="SETBACK_SIDE1",
        check_description=f"Side setback 1 for plot width {pw:.2f}m",
        required_m=required_m,
        proposed_m=prop,
    )


def check_side_setback_2(
    proposed_side2_m: float,
    plot_width_m: float,
    setback_table: list[dict],
    is_corner_plot: bool = False,
) -> dict:
    """Validate proposed side setback 2 against plot-width requirements and corner rules.

    Rule ID:
        SETBACK_SIDE2

    Rules:
        - For normal plots: standard side setback based on plot width.
        - For corner plots: standard side setback + 0.50m (facing second road).

    Args:
        proposed_side2_m: Proposed side 2 open space in metres.
        plot_width_m: Frontage / plot width in metres.
        setback_table: Parsed rows from setback_table.csv.
        is_corner_plot: Whether the plot is situated at a road junction.

    Returns:
        dict: Standard validation report dictionary.
    """
    prop = _validate_numeric(proposed_side2_m, "Proposed side setback 2", allow_zero=True)
    pw = _validate_numeric(plot_width_m, "Plot width", allow_zero=False)

    base_setback_m = lookup_setback(setback_table, "SIDE_REAR", pw)
    if is_corner_plot:
        required_m = base_setback_m + 0.50
        desc = f"Side setback 2 for corner plot (standard {base_setback_m:.2f}m + 0.50m second road)"
    else:
        required_m = base_setback_m
        desc = f"Side setback 2 for plot width {pw:.2f}m"

    return _evaluate_setback(
        rule_id="SETBACK_SIDE2",
        check_description=desc,
        required_m=required_m,
        proposed_m=prop,
    )


def check_rear_setback(
    proposed_rear_m: float,
    plot_width_m: float,
    setback_table: list[dict],
) -> dict:
    """Validate proposed rear setback against plot-width requirements.

    Rule ID:
        SETBACK_REAR

    Plot Width Bands:
        - Up to 9m inclusive: 1.00m
        - Above 9m to 12m inclusive: 1.50m
        - Above 12m: 2.00m

    Args:
        proposed_rear_m: Proposed rear open space in metres.
        plot_width_m: Frontage / plot width in metres.
        setback_table: Parsed rows from setback_table.csv.

    Returns:
        dict: Standard validation report dictionary.
    """
    prop = _validate_numeric(proposed_rear_m, "Proposed rear setback", allow_zero=True)
    pw = _validate_numeric(plot_width_m, "Plot width", allow_zero=False)

    required_m = lookup_setback(setback_table, "SIDE_REAR", pw)
    return _evaluate_setback(
        rule_id="SETBACK_REAR",
        check_description=f"Rear setback for plot width {pw:.2f}m",
        required_m=required_m,
        proposed_m=prop,
    )


def check_all_setbacks(
    application: dict,
    setback_table: list[dict],
) -> list[dict]:
    """Validate all four setbacks for a given application record.

    Precedence:
        Follows Ground Coverage in municipal evaluation precedence.
        Order of evaluation:
            1. SETBACK_FRONT
            2. SETBACK_SIDE1
            3. SETBACK_SIDE2
            4. SETBACK_REAR

    Args:
        application: Dictionary containing application fields (as parsed by data_loader).
        setback_table: Parsed rows from setback_table.csv.

    Returns:
        list[dict]: List of 4 validation report dictionaries.
    """
    is_corner = bool(application.get("is_corner_plot", False))
    return [
        check_front_setback(
            proposed_front_m=application["front_setback_m"],
            road_width_m=application["road_width_m"],
            setback_table=setback_table,
            is_corner_plot=is_corner,
            second_road_width_m=application.get("second_road_width_m"),
        ),
        check_side_setback_1(
            proposed_side1_m=application["side_setback_1_m"],
            plot_width_m=application["plot_width_m"],
            setback_table=setback_table,
        ),
        check_side_setback_2(
            proposed_side2_m=application["side_setback_2_m"],
            plot_width_m=application["plot_width_m"],
            setback_table=setback_table,
            is_corner_plot=is_corner,
        ),
        check_rear_setback(
            proposed_rear_m=application["rear_setback_m"],
            plot_width_m=application["plot_width_m"],
            setback_table=setback_table,
        ),
    ]


# ==============================================================================
# Height & Additional Floor Setback Validation
# ==============================================================================

def check_building_height(
    proposed_height_m: float,
    road_width_m: float,
    zone_id: str,
    zones: dict[str, dict],
    setback_table: list[dict],
    is_corner_plot: bool = False,
    second_road_width_m: float | None = None,
) -> dict:
    """Validate proposed building height against geometric road limits and zone caps.

    Formula / Rules:
        1. Geometric limit: 1.5 * (effective_road_width + required_front_setback)
        2. Zone height cap: from zones.csv based on road width:
           - Road width < 12m: height_cap_road_lt_12_m
           - Road width >= 12m: height_cap_road_ge_12_m
        3. Permitted max height = min(geometric_limit, zone_height_cap)

    Rule ID:
        HEIGHT_LIMIT

    Precedence:
        Follows Setbacks in municipal evaluation precedence.

    Compounding:
        False (height violations can never be compounded).

    Args:
        proposed_height_m: Total proposed building height in metres.
        road_width_m: Width of abutting road in metres.
        zone_id: Municipal zone identifier.
        zones: Dictionary of loaded zone records.
        setback_table: Parsed rows from setback_table.csv.
        is_corner_plot: Whether the plot is situated at a road corner.
        second_road_width_m: Optional width of secondary road for corner plots.

    Returns:
        dict: Standard validation report dictionary.
    """
    prop_h = _validate_numeric(proposed_height_m, "Proposed building height", allow_zero=False)
    rw1 = _validate_numeric(road_width_m, "Road width", allow_zero=False)

    effective_rw = rw1
    if is_corner_plot and second_road_width_m is not None:
        rw2 = _validate_numeric(second_road_width_m, "Second road width", allow_zero=False)
        effective_rw = max(rw1, rw2)

    clean_zone = zone_id.strip() if isinstance(zone_id, str) else str(zone_id)
    if clean_zone not in zones:
        raise ValueError(f"Unknown zone_id: {clean_zone!r}")

    zone = zones[clean_zone]
    req_front_setback = lookup_setback(setback_table, "FRONT", effective_rw)
    geometric_limit = 1.5 * (effective_rw + req_front_setback)

    if effective_rw < 12.0:
        zone_cap = zone["height_cap_road_lt_12_m"]
    else:
        zone_cap = zone["height_cap_road_ge_12_m"]

    max_allowed_height = min(geometric_limit, zone_cap)
    passed = prop_h <= max_allowed_height

    return {
        "passed": passed,
        "rule_id": "HEIGHT_LIMIT",
        "check": f"Height limit for road {effective_rw:.2f}m in zone {clean_zone}",
        "required": f"{max_allowed_height:.2f}m",
        "proposed": f"{prop_h:.2f}m",
        "compoundable": False,
    }


def calculate_extra_height_setback(
    floors_count: int,
    base_floor_limit: int,
    extra_per_floor: float = 0.5,
) -> float:
    """Calculate additional setback required on all sides for floors above a defined base allowance.

    Rule:
        Each additional floor above the base height allowance requires 0.5m extra setback on all sides.

    Note:
        The official PS-115 specification and sample data pack do not define a default
        base floor allowance (e.g. 4 floors). To preserve rule integrity without inventing
        unverified municipal rules, base_floor_limit must be provided explicitly.

    Args:
        floors_count: Number of storeys / floors above ground.
        base_floor_limit: Explicit number of floors included in the base height allowance.
        extra_per_floor: Extra setback required per floor exceeding the base (default 0.5m).

    Returns:
        float: Additional setback buffer in metres to add to all sides.
    """
    if isinstance(floors_count, bool) or not isinstance(floors_count, int):
        raise TypeError("Floors count must be an integer.")
    if isinstance(base_floor_limit, bool) or not isinstance(base_floor_limit, int):
        raise TypeError("base_floor_limit must be an integer.")
    if floors_count < 0:
        raise ValueError("Floors count cannot be negative.")
    if base_floor_limit < 0:
        raise ValueError("base_floor_limit cannot be negative.")

    if floors_count > base_floor_limit:
        return (floors_count - base_floor_limit) * extra_per_floor
    return 0.0


# ==============================================================================
# Parking Validation
# ==============================================================================

def calculate_required_parking(
    units_carpet_above_100: int = 0,
    units_carpet_upto_100: int = 0,
    commercial_built_up_sqm: float = 0.0,
    round_up: bool = False,
) -> float | int:
    """Calculate the minimum required car parking spaces.

    Formula:
        - Residential:
          - 1 car per unit with carpet area > 100 sq.m
          - 0.5 car per unit with carpet area <= 100 sq.m
        - Commercial:
          - 1 car per 50 sq.m of commercial built-up area
        - Total: residential + commercial

    Note:
        By default, returns the exact mathematical value without premature ceiling
        to prevent inventing unverified rounding rules not in the brief. If caller
        explicitly requests whole-car rounding, pass round_up=True.

    Args:
        units_carpet_above_100: Count of residential units with carpet > 100 sq.m.
        units_carpet_upto_100: Count of residential units with carpet <= 100 sq.m.
        commercial_built_up_sqm: Total commercial covered area in sq.m.
        round_up: If True, applies math.ceil. Defaults to False.

    Returns:
        float | int: Exact number of parking spaces required.
    """
    if isinstance(units_carpet_above_100, bool) or not isinstance(units_carpet_above_100, int):
        raise TypeError("units_carpet_above_100 must be an integer.")
    if isinstance(units_carpet_upto_100, bool) or not isinstance(units_carpet_upto_100, int):
        raise TypeError("units_carpet_upto_100 must be an integer.")
    if isinstance(commercial_built_up_sqm, bool) or not isinstance(commercial_built_up_sqm, (int, float)):
        raise TypeError("commercial_built_up_sqm must be a number (int or float).")

    if units_carpet_above_100 < 0 or units_carpet_upto_100 < 0:
        raise ValueError("Unit counts cannot be negative.")
    if commercial_built_up_sqm < 0:
        raise ValueError("Commercial built-up area cannot be negative.")

    res_need = (units_carpet_above_100 * 1.0) + (units_carpet_upto_100 * 0.5)
    comm_need = commercial_built_up_sqm / 50.0 if commercial_built_up_sqm > 0 else 0.0
    total = res_need + comm_need

    if round_up:
        return math.ceil(total)
    if total.is_integer():
        return int(total)
    return total


def check_parking(
    parking_proposed: int,
    units_carpet_above_100: int = 0,
    units_carpet_upto_100: int = 0,
    commercial_built_up_sqm: float = 0.0,
    round_up: bool = False,
) -> dict:
    """Validate proposed parking against municipal requirements and shortfall caps.

    Rule ID:
        PARKING

    Rule:
        - Shortfall = max(0, required - proposed)
        - Shortfall percentage = (shortfall / required) * 100
        - Shortfall <= 20%: ALLOWED (compliant with payment of Rs 200,000/car shortfall fee).
        - Shortfall > 20%: VIOLATION (non-compliant, cannot proceed).

    Returns:
        dict: Standard validation report dictionary.
    """
    if isinstance(parking_proposed, bool) or not isinstance(parking_proposed, int):
        raise TypeError("parking_proposed must be an integer.")
    if parking_proposed < 0:
        raise ValueError("Proposed parking cannot be negative.")

    required_bays = calculate_required_parking(
        units_carpet_above_100=units_carpet_above_100,
        units_carpet_upto_100=units_carpet_upto_100,
        commercial_built_up_sqm=commercial_built_up_sqm,
        round_up=round_up,
    )

    if required_bays == 0:
        shortfall = 0.0
        shortfall_pct = 0.0
        passed = True
    else:
        shortfall = max(0.0, float(required_bays) - parking_proposed)
        shortfall_pct = (shortfall / float(required_bays)) * 100.0
        # Tolerated up to exactly 20.0% shortfall
        passed = round(shortfall_pct, 4) <= 20.0

    req_display = f"{int(required_bays)} cars" if isinstance(required_bays, int) or required_bays.is_integer() else f"{required_bays:.2f} cars"
    shortfall_display = int(shortfall) if shortfall.is_integer() else round(shortfall, 2)

    return {
        "passed": passed,
        "rule_id": "PARKING",
        "check": f"Parking requirement ({req_display} required, max 20% shortfall allowed)",
        "required": req_display,
        "proposed": f"{parking_proposed} cars",
        "compoundable": False,
        "shortfall": shortfall_display,
        "shortfall_pct": round(shortfall_pct, 2),
    }

