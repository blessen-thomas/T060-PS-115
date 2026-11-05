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

from src.data_loader import lookup_max_coverage


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

