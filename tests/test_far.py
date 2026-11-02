"""Automated Unit Tests for FAR Calculation and Compliance Validation.

These tests cover:
1. Normal valid FAR calculation.
2. Boundary values (e.g. 0 built-up area, FAR exactly equal to allowed limit).
3. Compliance status when within allowed FAR.
4. Non-compliance status when FAR exceeds allowed limit.
5. Rejection of invalid inputs (zero/negative plot area, negative built-up area, negative allowed FAR).
6. Type validation (rejecting non-numeric types and booleans).
"""

import pytest
from src.far import calculate_far, get_base_far, validate_far


# ==============================================================================
# 1. Calculation Tests (Normal & Boundary)
# ==============================================================================

def test_calculate_far_standard():
    """Verify standard calculation: 1500 sq.m built-up on 1000 sq.m plot gives FAR 1.5."""
    assert calculate_far(plot_area=1000.0, eligible_built_up_area=1500.0) == 1.5


def test_calculate_far_fractional():
    """Verify fractional precision: 2500 sq.m on 1500 sq.m plot returns exact ratio."""
    # 2500 / 1500 = 1.666666...
    assert calculate_far(plot_area=1500.0, eligible_built_up_area=2500.0) == pytest.approx(1.6666667)


def test_calculate_far_zero_built_up_area():
    """A vacant plot with 0 built-up area has an FAR of 0.0."""
    assert calculate_far(plot_area=500.0, eligible_built_up_area=0.0) == 0.0


# ==============================================================================
# 2. Input Validation Tests (Rejections & Exceptions)
# ==============================================================================

def test_calculate_far_rejects_zero_plot_area():
    """Plot area of 0 must be rejected with ValueError (cannot divide by zero)."""
    with pytest.raises(ValueError, match="Plot area must be greater than zero"):
        calculate_far(plot_area=0, eligible_built_up_area=100)


def test_calculate_far_rejects_negative_plot_area():
    """Negative plot area must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Plot area must be greater than zero"):
        calculate_far(plot_area=-500, eligible_built_up_area=100)


def test_calculate_far_rejects_negative_built_up_area():
    """Negative built-up area must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Eligible built-up area cannot be negative"):
        calculate_far(plot_area=1000, eligible_built_up_area=-50)


def test_validate_far_rejects_negative_allowed_far():
    """Negative allowed FAR limit must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Allowed FAR cannot be negative"):
        validate_far(plot_area=1000, eligible_built_up_area=500, allowed_far=-1.0)


def test_calculate_far_rejects_non_numeric_type():
    """String inputs must be rejected with TypeError."""
    with pytest.raises(TypeError, match="must be a number"):
        calculate_far(plot_area="1000", eligible_built_up_area=500)  # type: ignore


def test_calculate_far_rejects_boolean_type():
    """Boolean True/False must not be treated as 1/0."""
    with pytest.raises(TypeError, match="must be a number"):
        calculate_far(plot_area=True, eligible_built_up_area=500)  # type: ignore


# ==============================================================================
# 3. Compliance Validation Tests (Within Limit, Boundary, Exceeding)
# ==============================================================================

def test_validate_far_within_limit():
    """Calculated FAR below permitted FAR should be compliant."""
    # Plot 1000, built-up 1200 -> FAR 1.2 <= allowed 1.5
    result = validate_far(plot_area=1000, eligible_built_up_area=1200, allowed_far=1.5)

    assert result["is_compliant"] is True
    assert result["calculated_far"] == 1.2
    assert result["allowed_far"] == 1.5
    assert "within the permitted limit" in result["message"]


def test_validate_far_exactly_at_limit():
    """Calculated FAR exactly equal to permitted FAR is compliant."""
    # Plot 1000, built-up 1500 -> FAR 1.5 == allowed 1.5
    result = validate_far(plot_area=1000, eligible_built_up_area=1500, allowed_far=1.5)

    assert result["is_compliant"] is True
    assert result["calculated_far"] == 1.5
    assert "within the permitted limit" in result["message"]


def test_validate_far_exceeding_limit():
    """Calculated FAR above permitted FAR should be non-compliant."""
    # Plot 1000, built-up 2000 -> FAR 2.0 > allowed 1.5
    result = validate_far(plot_area=1000, eligible_built_up_area=2000, allowed_far=1.5)

    assert result["is_compliant"] is False
    assert result["calculated_far"] == 2.0
    assert result["allowed_far"] == 1.5
    assert "exceeds the permitted limit" in result["message"]


def test_validate_far_slight_overage_not_masked_by_rounding():
    """Verify that an FAR slightly above allowed limit is NOT falsely approved due to rounding.

    Scenario:
        Plot Area = 10,000 sq.m, Built-up Area = 15,000.4 sq.m, Allowed FAR = 1.5
        Actual FAR = 15000.4 / 10000.0 = 1.50004.
        Both 1.50004 and 1.5000 round to 1.5000 at four decimal places.
        If rounded before comparison, 1.5000 <= 1.5 would be True (false approval).
        The engine must reject this plan as non-compliant.
    """
    result = validate_far(
        plot_area=10000.0,
        eligible_built_up_area=15000.4,
        allowed_far=1.5,
    )

    assert result["is_compliant"] is False
    assert result["calculated_far"] == 1.50004
    assert result["allowed_far"] == 1.5
    assert "exceeds the permitted limit" in result["message"]


# ==============================================================================
# 4. Base FAR Lookup Tests (Building Use & Road Width Bands)
# ==============================================================================

def test_base_far_band_below_12m():
    """Verify Band 1 (road width < 12m): Residential/Mixed=1.75, Commercial=2.00."""
    road = 9.0
    assert get_base_far("residential", road) == 1.75
    assert get_base_far("commercial", road) == 2.00
    assert get_base_far("mixed_use", road) == 1.75


def test_base_far_band_12m_to_18m_mid():
    """Verify Band 2 (12m <= road width <= 18m) mid-range: Residential/Mixed=2.25, Commercial=2.50."""
    road = 15.0
    assert get_base_far("residential", road) == 2.25
    assert get_base_far("commercial", road) == 2.50
    assert get_base_far("mixed_use", road) == 2.25


def test_base_far_band_above_18m():
    """Verify Band 3 (road width > 18m): Residential/Mixed=2.50, Commercial=2.75."""
    road = 24.0
    assert get_base_far("residential", road) == 2.50
    assert get_base_far("commercial", road) == 2.75
    assert get_base_far("mixed_use", road) == 2.50


# ==============================================================================
# 5. Boundary Condition Tests (Exactly 12m and Exactly 18m)
# ==============================================================================

def test_base_far_boundary_exactly_12m():
    """Road width of exactly 12m falls into Band 2 (from 12m through 18m)."""
    assert get_base_far("residential", 12.0) == 2.25
    assert get_base_far("commercial", 12.0) == 2.50
    assert get_base_far("mixed_use", 12.0) == 2.25


def test_base_far_boundary_exactly_18m():
    """Road width of exactly 18m falls into Band 2 (from 12m through 18m)."""
    assert get_base_far("residential", 18.0) == 2.25
    assert get_base_far("commercial", 18.0) == 2.50
    assert get_base_far("mixed_use", 18.0) == 2.25


def test_base_far_boundary_just_below_12m():
    """Road width of 11.99m is strictly below 12m -> falls into Band 1."""
    assert get_base_far("residential", 11.99) == 1.75
    assert get_base_far("commercial", 11.99) == 2.00
    assert get_base_far("mixed_use", 11.99) == 1.75


def test_base_far_boundary_just_above_18m():
    """Road width of 18.01m is strictly above 18m -> falls into Band 3."""
    assert get_base_far("residential", 18.01) == 2.50
    assert get_base_far("commercial", 18.01) == 2.75
    assert get_base_far("mixed_use", 18.01) == 2.50


# ==============================================================================
# 6. Base FAR Input Validation & String Normalization Tests
# ==============================================================================

def test_base_far_rejects_zero_or_negative_road_width():
    """Road width <= 0 must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Road width must be greater than zero"):
        get_base_far("residential", 0)

    with pytest.raises(ValueError, match="Road width must be greater than zero"):
        get_base_far("residential", -5.0)


def test_base_far_rejects_non_numeric_road_width():
    """Non-numeric or boolean road widths must be rejected with TypeError."""
    with pytest.raises(TypeError, match="must be a number"):
        get_base_far("residential", "12m")  # type: ignore

    with pytest.raises(TypeError, match="must be a number"):
        get_base_far("residential", True)  # type: ignore


def test_base_far_rejects_unsupported_building_use():
    """Unsupported building uses must raise ValueError with clear guidance."""
    with pytest.raises(ValueError, match="Unsupported building use"):
        get_base_far("industrial", 12.0)

    with pytest.raises(ValueError, match="Unsupported building use"):
        get_base_far("agricultural", 15.0)


def test_base_far_rejects_non_string_building_use():
    """Non-string building use must raise TypeError."""
    with pytest.raises(TypeError, match="Building use must be a string"):
        get_base_far(123, 12.0)  # type: ignore


def test_base_far_string_normalization():
    """Case variations, whitespace, and hyphens/spaces should be handled smoothly."""
    assert get_base_far("  Residential  ", 10.0) == 1.75
    assert get_base_far("COMMERCIAL", 10.0) == 2.00
    assert get_base_far("Mixed Use", 15.0) == 2.25
    assert get_base_far("mixed-use", 15.0) == 2.25


# ==============================================================================
# 7. Integration: validate_far with Automatic Base FAR Determination
# ==============================================================================

def test_validate_far_with_building_use_and_road_width():
    """validate_far can derive allowed FAR directly from building use and road width."""
    # Plot 1000 sq.m, built-up 2000 sq.m on a 12m road for residential -> base FAR 2.25
    # Calculated FAR = 2000 / 1000 = 2.0 <= 2.25 -> COMPLIANT
    result = validate_far(
        plot_area=1000.0,
        eligible_built_up_area=2000.0,
        building_use="residential",
        road_width=12.0,
    )

    assert result["is_compliant"] is True
    assert result["allowed_far"] == 2.25
    assert result["calculated_far"] == 2.0
    assert result["building_use"] == "residential"
    assert result["road_width"] == 12.0
