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

from src.data_loader import lookup_max_coverage, lookup_setback


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

