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

