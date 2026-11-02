"""Floor Area Ratio (FAR) Calculation and Compliance Module.

Business Rules:
1. FAR Calculation:
   - FAR = eligible_built_up_area / plot_area.
   - Plan is compliant if calculated FAR <= allowed FAR.

2. Base FAR Lookup (by Building Use and Road Width):
   - Residential:
       - Road width < 12 m  -> FAR 1.75
       - Road width 12 m through 18 m (12 <= width <= 18) -> FAR 2.25
       - Road width > 18 m  -> FAR 2.50
   - Commercial:
       - Add 0.25 to the residential FAR for the corresponding road-width band.
   - Mixed Use:
       - Same as the residential FAR for the corresponding road-width band.

Validation Rules:
- Plot area must be strictly > 0.
- Eligible built-up area must be >= 0.
- Road width must be strictly > 0.
- Building use must be one of: 'residential', 'commercial', 'mixed_use'.
- Allowed FAR must be >= 0.
"""

# Supported building-use categories
VALID_BUILDING_USES = ("residential", "commercial", "mixed_use")


def _ensure_number(value, field_name: str) -> float:
    """Helper function to verify that an input is a valid real number.

    Booleans are explicitly rejected because in Python, bool is a subclass
    of int (True == 1, False == 0).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number (int or float).")
    return float(value)


def get_base_far(building_use: str, road_width: float) -> float:
    """Determine permitted base FAR based on building use and abutting road width.

    Municipal Bands:
    - Below 12 m:
        Residential: 1.75 | Commercial: 2.00 | Mixed Use: 1.75
    - From 12 m through 18 m (inclusive of 12 and 18):
        Residential: 2.25 | Commercial: 2.50 | Mixed Use: 2.25
    - Above 18 m:
        Residential: 2.50 | Commercial: 2.75 | Mixed Use: 2.50

    Args:
        building_use: Use category ('residential', 'commercial', 'mixed_use').
        road_width: Width of abutting road in metres.

    Returns:
        float: Permitted base FAR.

    Raises:
        TypeError: If road_width is not a number or building_use is not a string.
        ValueError: If road_width <= 0 or building_use is not recognized.
    """
    if not isinstance(building_use, str):
        raise TypeError("Building use must be a string.")

    # Normalize: strip spaces, convert to lowercase, convert spaces/hyphens to underscores
    normalized_use = building_use.strip().lower().replace(" ", "_").replace("-", "_")

    if normalized_use not in VALID_BUILDING_USES:
        valid_display = ", ".join(repr(u) for u in VALID_BUILDING_USES)
        raise ValueError(
            f"Unsupported building use: {building_use!r}. "
            f"Supported uses are: {valid_display}."
        )

    width = _ensure_number(road_width, "Road width")
    if width <= 0:
        raise ValueError("Road width must be greater than zero.")

    # Step 1: Determine base FAR for Residential
    if width < 12.0:
        residential_far = 1.75
    elif width <= 18.0:
        residential_far = 2.25
    else:
        residential_far = 2.50

    # Step 2: Apply building use rules
    # Mixed use matches residential; Commercial gets +0.25 bonus
    if normalized_use in ("residential", "mixed_use"):
        return residential_far
    elif normalized_use == "commercial":
        return round(residential_far + 0.25, 4)


def calculate_far(plot_area: float, eligible_built_up_area: float) -> float:
    """Calculate the Floor Area Ratio (FAR).

    Formula:
        FAR = eligible_built_up_area / plot_area

    Args:
        plot_area: Total area of the site/plot (in square units).
        eligible_built_up_area: Total covered/built-up area counted towards FAR.

    Returns:
        float: Calculated exact FAR (unrounded).

    Raises:
        TypeError: If plot_area or eligible_built_up_area is not a number.
        ValueError: If plot_area is <= 0 or eligible_built_up_area is < 0.
    """
    plot_num = _ensure_number(plot_area, "Plot area")
    built_num = _ensure_number(eligible_built_up_area, "Eligible built-up area")

    if plot_num <= 0:
        raise ValueError("Plot area must be greater than zero.")

    if built_num < 0:
        raise ValueError("Eligible built-up area cannot be negative.")

    # Calculate exact FAR without premature rounding.
    # Rounding before comparison can cause non-compliant plans to be falsely approved.
    return built_num / plot_num


def validate_far(
    plot_area: float,
    eligible_built_up_area: float,
    allowed_far: float | None = None,
    building_use: str | None = None,
    road_width: float | None = None,
) -> dict:
    """Validate whether the proposed FAR complies with the allowed municipal limit.

    The permitted FAR can either be passed directly via `allowed_far`, or
    determined automatically from `building_use` and `road_width`.

    Args:
        plot_area: Total area of the plot.
        eligible_built_up_area: Total eligible covered area proposed.
        allowed_far: Maximum FAR permitted (if known directly).
        building_use: 'residential', 'commercial', or 'mixed_use' (optional if allowed_far given).
        road_width: Road width in metres (optional if allowed_far given).

    Returns:
        dict: A dictionary containing:
            - plot_area: The plot area provided.
            - eligible_built_up_area: The built-up area provided.
            - allowed_far: The permitted FAR limit.
            - calculated_far: The calculated FAR.
            - is_compliant: True if calculated_far <= allowed_far, else False.
            - message: A human-readable compliance explanation.
            - building_use: The building use (if provided, else None).
            - road_width: The road width (if provided, else None).

    Raises:
        TypeError: If any input is not the expected type.
        ValueError: If inputs violate validation rules or if neither allowed_far nor
                    (building_use and road_width) is provided.
    """
    if allowed_far is None:
        if building_use is None or road_width is None:
            raise ValueError(
                "Must provide either 'allowed_far' or both 'building_use' and 'road_width'."
            )
        allowed_num = get_base_far(building_use, road_width)
    else:
        allowed_num = _ensure_number(allowed_far, "Allowed FAR")
        if allowed_num < 0:
            raise ValueError("Allowed FAR cannot be negative.")

    calculated_far = calculate_far(plot_area, eligible_built_up_area)
    is_compliant = calculated_far <= allowed_num

    if is_compliant:
        message = "FAR is within the permitted limit."
    else:
        excess = calculated_far - allowed_num
        message = f"FAR exceeds the permitted limit by {excess:.6g}."

    return {
        "plot_area": float(plot_area),
        "eligible_built_up_area": float(eligible_built_up_area),
        "allowed_far": allowed_num,
        "calculated_far": calculated_far,
        "is_compliant": is_compliant,
        "message": message,
        "building_use": building_use,
        "road_width": float(road_width) if road_width is not None else None,
    }
