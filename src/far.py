"""Floor Area Ratio (FAR) Calculation and Compliance Module.

Business Rule:
- FAR is defined as the eligible built-up area divided by the plot area.
- FAR = eligible_built_up_area / plot_area.
- A proposed plan is compliant if the calculated FAR is less than or equal
  to the permitted (allowed) FAR.

Validation Rules:
- Plot area must be strictly greater than 0 (cannot divide by zero or negative).
- Eligible built-up area cannot be negative (can be 0 for vacant/open plot).
- Allowed FAR must be greater than or equal to 0.
"""


def _ensure_number(value, field_name: str) -> float:
    """Helper function to verify that an input is a valid real number.

    Booleans are explicitly rejected because in Python, bool is a subclass
    of int (True == 1, False == 0).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number (int or float).")
    return float(value)


def calculate_far(plot_area: float, eligible_built_up_area: float) -> float:
    """Calculate the Floor Area Ratio (FAR).

    Formula:
        FAR = eligible_built_up_area / plot_area

    Args:
        plot_area: Total area of the site/plot (in square units).
        eligible_built_up_area: Total covered/built-up area counted towards FAR.

    Returns:
        float: Calculated FAR rounded to 4 decimal places.

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

    # Calculate FAR and round to 4 decimal places for precision & readability
    far_value = built_num / plot_num
    return round(far_value, 4)


def validate_far(
    plot_area: float,
    eligible_built_up_area: float,
    allowed_far: float,
) -> dict:
    """Validate whether the proposed FAR complies with the allowed municipal limit.

    Args:
        plot_area: Total area of the plot.
        eligible_built_up_area: Total eligible covered area proposed.
        allowed_far: Maximum FAR permitted by municipal zoning/regulations.

    Returns:
        dict: A dictionary containing:
            - plot_area: The plot area provided.
            - eligible_built_up_area: The built-up area provided.
            - allowed_far: The allowed FAR limit.
            - calculated_far: The calculated FAR.
            - is_compliant: True if calculated_far <= allowed_far, else False.
            - message: A human-readable compliance explanation.

    Raises:
        TypeError: If any input is not numeric.
        ValueError: If inputs violate validation rules.
    """
    allowed_num = _ensure_number(allowed_far, "Allowed FAR")
    if allowed_num < 0:
        raise ValueError("Allowed FAR cannot be negative.")

    calculated_far = calculate_far(plot_area, eligible_built_up_area)
    is_compliant = calculated_far <= allowed_num

    if is_compliant:
        message = "FAR is within the permitted limit."
    else:
        message = (
            f"FAR exceeds the permitted limit by "
            f"{round(calculated_far - allowed_num, 4)}."
        )

    return {
        "plot_area": float(plot_area),
        "eligible_built_up_area": float(eligible_built_up_area),
        "allowed_far": allowed_num,
        "calculated_far": calculated_far,
        "is_compliant": is_compliant,
        "message": message,
    }
