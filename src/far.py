"""Floor Area Ratio (FAR) Calculation and Compliance Module.

Business Rules:
1. FAR Calculation:
   - FAR = eligible_built_up_area / plot_area.
   - Plan is compliant if calculated FAR <= allowed FAR.

2. Eligible Built-up Area Exclusions:
   - Excluded from FAR:
       - 100% of Stilt Parking Area
       - 100% of Parking Basement Area
       - 10% of Balcony Area
   - Eligible Built-up Area = Total Built-up Area
                            - Stilt Parking Area
                            - Parking Basement Area
                            - (0.10 * Balcony Area)

3. Base FAR Lookup (by Building Use and Road Width):
   - Residential:
       - Road width < 12 m  -> FAR 1.75
       - Road width 12 m through 18 m (12 <= width <= 18) -> FAR 2.25
       - Road width > 18 m  -> FAR 2.50
   - Commercial:
       - Add 0.25 to the residential FAR for the corresponding road-width band.
   - Mixed Use:
       - Same as the residential FAR for the corresponding road-width band.

4. Premium FAR:
   - Maximum additional FAR: 0.5.
   - Available only if road width >= 12 metres.
   - Residential charge: 40% of guidance value per sq.m.
   - Commercial charge: 60% of guidance value per sq.m.

5. Transferable Development Rights (TDR) & Combined Cap:
   - TDR can add up to 0.4 FAR.
   - Premium FAR + TDR together cannot exceed 0.6 (Combined cap = Base FAR + 0.6).
   - Final Permitted FAR = Base FAR + Premium FAR + TDR FAR.

Validation Rules:
- Plot area must be strictly > 0.
- Areas cannot be negative; total excluded area cannot exceed total built-up area.
- Road width must be strictly > 0.
- Building use must be one of: 'residential', 'commercial', 'mixed_use'.
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


def calculate_eligible_built_up_area(
    total_built_up_area: float,
    stilt_parking_area: float = 0.0,
    basement_parking_area: float = 0.0,
    balcony_area: float = 0.0,
) -> float:
    """Calculate the eligible built-up area counted towards FAR.

    Official Rule:
        FAR is calculated using eligible built-up area divided by plot area.
        Excluded areas:
        - 100% of stilt parking area
        - 100% of parking basement area
        - 10% of balcony area (90% is counted towards FAR)

        Eligible Built-up Area = Total Built-up Area
                                 - Stilt Parking Area
                                 - Parking Basement Area
                                 - (0.10 * Balcony Area)

    Args:
        total_built_up_area: Total constructed/covered area in square metres.
        stilt_parking_area: Dedicated stilt parking area in square metres.
        basement_parking_area: Dedicated basement parking area in square metres.
        balcony_area: Total balcony area in square metres.

    Returns:
        float: Eligible built-up area rounded to 4 decimal places.

    Raises:
        TypeError: If any area argument is not numeric.
        ValueError: If any area is negative, or if total excluded area exceeds
                    total built-up area.
    """
    total = _ensure_number(total_built_up_area, "Total built-up area")
    stilt = _ensure_number(stilt_parking_area, "Stilt parking area")
    basement = _ensure_number(basement_parking_area, "Basement parking area")
    balcony = _ensure_number(balcony_area, "Balcony area")

    if total < 0:
        raise ValueError("Total built-up area cannot be negative.")
    if stilt < 0:
        raise ValueError("Stilt parking area cannot be negative.")
    if basement < 0:
        raise ValueError("Basement parking area cannot be negative.")
    if balcony < 0:
        raise ValueError("Balcony area cannot be negative.")

    excluded_balcony = 0.10 * balcony
    total_excluded = round(stilt + basement + excluded_balcony, 4)

    if total_excluded > total:
        raise ValueError(
            f"Total excluded area ({total_excluded} sq.m) cannot exceed "
            f"total built-up area ({total} sq.m)."
        )

    eligible = total - total_excluded
    return round(eligible, 4)


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


def validate_premium_far(premium_far: float, road_width: float) -> float:
    """Validate requested premium FAR against municipal regulations.

    Rules:
    - Premium FAR allows an additional FAR of up to 0.5.
    - Premium FAR is available only for roads with width of at least 12 metres.

    Args:
        premium_far: Additional FAR requested (between 0.0 and 0.5).
        road_width: Abutting road width in metres.

    Returns:
        float: Validated premium FAR.

    Raises:
        TypeError: If premium_far or road_width is not numeric.
        ValueError: If premium_far < 0, premium_far > 0.5, or road_width < 12.0 when premium_far > 0.
    """
    prem_num = _ensure_number(premium_far, "Premium FAR")
    width_num = _ensure_number(road_width, "Road width")

    if prem_num < 0:
        raise ValueError("Premium FAR cannot be negative.")

    if prem_num > 0.5:
        raise ValueError(
            f"Premium FAR requested ({prem_num}) exceeds maximum allowed limit of 0.5."
        )

    if prem_num > 0 and width_num < 12.0:
        raise ValueError(
            f"Premium FAR requires an abutting road width of at least 12 metres (current: {width_num} m)."
        )

    return prem_num


def calculate_premium_far_rate(building_use: str, guidance_value: float) -> float:
    """Calculate the applicable premium FAR charge rate per square metre.

    Official Percentages:
    - Residential: 40% of guidance value per square metre.
    - Commercial: 60% of guidance value per square metre.

    Args:
        building_use: Category ('residential' or 'commercial').
        guidance_value: Government guidance value in currency per square metre.

    Returns:
        float: Applicable charge rate per square metre.

    Raises:
        TypeError: If guidance_value is not numeric or building_use is not a string.
        ValueError: If guidance_value < 0 or building use is unsupported/unspecified.
    """
    if not isinstance(building_use, str):
        raise TypeError("Building use must be a string.")

    guidance_num = _ensure_number(guidance_value, "Guidance value")
    if guidance_num < 0:
        raise ValueError("Guidance value cannot be negative.")

    normalized_use = building_use.strip().lower().replace(" ", "_").replace("-", "_")

    if normalized_use == "residential":
        rate_percentage = 0.40
    elif normalized_use == "commercial":
        rate_percentage = 0.60
    elif normalized_use == "mixed_use":
        # Mixed use is flagged as an ambiguity because the official rules
        # specify 40% for residential and 60% for commercial without defining mixed use.
        raise ValueError(
            "Premium FAR rate for 'mixed_use' is not defined in official rules. "
            "Only 'residential' (40%) and 'commercial' (60%) are specified."
        )
    else:
        raise ValueError(f"Unsupported building use for premium FAR: {building_use!r}.")

    return round(rate_percentage * guidance_num, 2)


def calculate_premium_far_charge(
    premium_far: float,
    plot_area: float,
    building_use: str,
    guidance_value: float,
) -> dict:
    """Calculate the total fee for purchasing premium FAR.

    Calculation:
        Chargeable Area (sq.m) = premium_far * plot_area
        Rate per sq.m = rate_percentage * guidance_value
        Total Premium Charge = Chargeable Area * Rate per sq.m

    Args:
        premium_far: Additional premium FAR requested (0.0 to 0.5).
        plot_area: Total plot area in square metres.
        building_use: 'residential' or 'commercial'.
        guidance_value: Government guidance value per square metre.

    Returns:
        dict: Detailed breakdown of the premium FAR charge.
    """
    prem_num = _ensure_number(premium_far, "Premium FAR")
    plot_num = _ensure_number(plot_area, "Plot area")

    if prem_num < 0:
        raise ValueError("Premium FAR cannot be negative.")
    if prem_num > 0.5:
        raise ValueError(f"Premium FAR requested ({prem_num}) exceeds maximum allowed limit of 0.5.")
    if plot_num <= 0:
        raise ValueError("Plot area must be greater than zero.")

    rate_per_sqm = calculate_premium_far_rate(building_use, guidance_value)
    chargeable_area = round(prem_num * plot_num, 4)
    total_charge = round(chargeable_area * rate_per_sqm, 2)

    normalized_use = building_use.strip().lower().replace(" ", "_").replace("-", "_")
    rate_pct = 0.40 if normalized_use == "residential" else 0.60

    return {
        "premium_far": prem_num,
        "plot_area": plot_num,
        "building_use": normalized_use,
        "guidance_value": float(guidance_value),
        "rate_percentage": rate_pct,
        "rate_per_sqm": rate_per_sqm,
        "chargeable_area": chargeable_area,
        "total_charge": total_charge,
    }


def validate_tdr_far(tdr_far: float) -> float:
    """Validate requested Transferable Development Rights (TDR) FAR.

    Rule:
    - TDR can add up to 0.4 FAR.

    Args:
        tdr_far: Additional FAR requested via TDR.

    Returns:
        float: Validated TDR FAR.

    Raises:
        TypeError: If tdr_far is not numeric.
        ValueError: If tdr_far < 0 or tdr_far > 0.4.
    """
    tdr_num = _ensure_number(tdr_far, "TDR FAR")

    if tdr_num < 0:
        raise ValueError("TDR FAR cannot be negative.")

    if tdr_num > 0.4:
        raise ValueError(
            f"TDR FAR requested ({tdr_num}) exceeds maximum allowed limit of 0.4."
        )

    return tdr_num


def calculate_final_permitted_far(
    base_far: float,
    premium_far: float = 0.0,
    tdr_far: float = 0.0,
    road_width: float | None = None,
) -> float:
    """Calculate the final permitted FAR combining Base FAR, Premium FAR, and TDR.

    Rules:
    - Base FAR must be > 0.
    - Premium FAR <= 0.5 (requires road width >= 12m if road_width provided).
    - TDR FAR <= 0.4.
    - Premium FAR and TDR together cannot exceed 0.6 (Combined cap = Base FAR + 0.6).
    - Final Permitted FAR = Base FAR + Premium FAR + TDR FAR.

    Example Edge Case:
        Premium FAR = 0.5, TDR = 0.4 -> Combined additional FAR = 0.9.
        Maximum combined additional FAR = 0.6.
        Excess = 0.3.
        Rejected with ValueError (values are never silently modified).

    Args:
        base_far: Base permitted FAR.
        premium_far: Additional premium FAR (max 0.5).
        tdr_far: Additional TDR FAR (max 0.4).
        road_width: Abutting road width in metres (optional).

    Returns:
        float: Final permitted FAR rounded to 4 decimal places.

    Raises:
        TypeError: If any input is not numeric.
        ValueError: If any limit or the combined cap is exceeded.
    """
    base_num = _ensure_number(base_far, "Base FAR")
    if base_num <= 0:
        raise ValueError("Base FAR must be greater than zero.")

    if road_width is not None:
        prem_num = validate_premium_far(premium_far, road_width)
    else:
        prem_num = _ensure_number(premium_far, "Premium FAR")
        if prem_num < 0:
            raise ValueError("Premium FAR cannot be negative.")
        if prem_num > 0.5:
            raise ValueError(f"Premium FAR requested ({prem_num}) exceeds maximum allowed limit of 0.5.")

    tdr_num = validate_tdr_far(tdr_far)

    combined_additional = round(prem_num + tdr_num, 4)
    if combined_additional > 0.6:
        excess = round(combined_additional - 0.6, 4)
        raise ValueError(
            f"Combined additional FAR (Premium FAR {prem_num} + TDR {tdr_num} = {combined_additional}) "
            f"exceeds the maximum combined limit of 0.6 by {excess}."
        )

    return round(base_num + combined_additional, 4)


def validate_far(
    plot_area: float,
    eligible_built_up_area: float | None = None,
    allowed_far: float | None = None,
    building_use: str | None = None,
    road_width: float | None = None,
    total_built_up_area: float | None = None,
    stilt_parking_area: float = 0.0,
    basement_parking_area: float = 0.0,
    balcony_area: float = 0.0,
    premium_far: float = 0.0,
    tdr_far: float = 0.0,
) -> dict:
    """Validate whether the proposed building plan complies with municipal FAR limits.

    Supports:
    - Direct eligible built-up area OR total built-up area with deductions.
    - Direct allowed FAR OR base FAR derived from building use and road width.
    - Optional Premium FAR and TDR additional FAR components with combined cap enforcement.

    Args:
        plot_area: Total area of the plot (sq.m).
        eligible_built_up_area: Direct eligible built-up area (sq.m).
        allowed_far: Directly specified permitted FAR limit.
        building_use: 'residential', 'commercial', or 'mixed_use'.
        road_width: Road width in metres.
        total_built_up_area: Total built-up area before exclusions (sq.m).
        stilt_parking_area: Dedicated stilt parking area (sq.m).
        basement_parking_area: Dedicated basement parking area (sq.m).
        balcony_area: Total balcony area (sq.m).
        premium_far: Additional premium FAR requested (max 0.5).
        tdr_far: Additional TDR FAR requested (max 0.4).

    Returns:
        dict: Complete compliance evaluation report.

    Raises:
        TypeError: If inputs have invalid types.
        ValueError: If validation checks or municipal caps fail.
    """
    # 1. Resolve Eligible Built-Up Area
    if eligible_built_up_area is not None:
        eligible_num = _ensure_number(eligible_built_up_area, "Eligible built-up area")
    elif total_built_up_area is not None:
        eligible_num = calculate_eligible_built_up_area(
            total_built_up_area=total_built_up_area,
            stilt_parking_area=stilt_parking_area,
            basement_parking_area=basement_parking_area,
            balcony_area=balcony_area,
        )
    else:
        raise ValueError("Must provide either 'eligible_built_up_area' or 'total_built_up_area'.")

    # 2. Resolve Base Allowed FAR
    if allowed_far is not None:
        base_num = _ensure_number(allowed_far, "Allowed FAR")
        if base_num < 0:
            raise ValueError("Allowed FAR cannot be negative.")
    elif building_use is not None and road_width is not None:
        base_num = get_base_far(building_use, road_width)
    else:
        raise ValueError(
            "Must provide either 'allowed_far' or both 'building_use' and 'road_width'."
        )

    # 3. Resolve Additional FAR (Premium & TDR) and Final Permitted FAR
    prem_num = _ensure_number(premium_far, "Premium FAR")
    tdr_num = _ensure_number(tdr_far, "TDR FAR")

    if prem_num > 0 or tdr_num > 0:
        final_permitted_far = calculate_final_permitted_far(
            base_far=base_num,
            premium_far=prem_num,
            tdr_far=tdr_num,
            road_width=road_width,
        )
    else:
        final_permitted_far = base_num

    # 4. Perform Compliance Check
    calculated_far = calculate_far(plot_area, eligible_num)
    is_compliant = calculated_far <= final_permitted_far

    if is_compliant:
        message = "FAR is within the permitted limit."
    else:
        excess = calculated_far - final_permitted_far
        message = f"FAR exceeds the permitted limit by {excess:.6g}."

    return {
        "plot_area": float(plot_area),
        "eligible_built_up_area": eligible_num,
        "total_built_up_area": float(total_built_up_area) if total_built_up_area is not None else None,
        "base_far": base_num,
        "premium_far": prem_num,
        "tdr_far": tdr_num,
        "allowed_far": final_permitted_far,
        "calculated_far": calculated_far,
        "is_compliant": is_compliant,
        "message": message,
        "building_use": building_use,
        "road_width": float(road_width) if road_width is not None else None,
    }
