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
from src.far import (
    calculate_eligible_built_up_area,
    calculate_far,
    calculate_final_permitted_far,
    calculate_premium_far_charge,
    calculate_premium_far_rate,
    get_base_far,
    validate_far,
    validate_premium_far,
    validate_tdr_far,
)


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


# ==============================================================================
# 8. Eligible Built-up Area Tests (Task 1)
# ==============================================================================

def test_eligible_built_up_area_standard():
    """Verify exclusions: Stilt (100%), Basement (100%), Balcony (10%).

    Example:
        Total: 1000 sq.m
        Stilt: 150 sq.m
        Basement: 200 sq.m
        Balcony: 100 sq.m (10% = 10 sq.m excluded)
        Total Excluded = 150 + 200 + 10 = 360 sq.m
        Eligible = 1000 - 360 = 640 sq.m
    """
    eligible = calculate_eligible_built_up_area(
        total_built_up_area=1000.0,
        stilt_parking_area=150.0,
        basement_parking_area=200.0,
        balcony_area=100.0,
    )
    assert eligible == 640.0


def test_eligible_built_up_area_zero_exclusions():
    """When no exclusions apply, eligible built-up area equals total area."""
    eligible = calculate_eligible_built_up_area(
        total_built_up_area=1200.0,
        stilt_parking_area=0.0,
        basement_parking_area=0.0,
        balcony_area=0.0,
    )
    assert eligible == 1200.0


def test_eligible_built_up_area_boundary_full_deduction():
    """Boundary: When total excluded area equals total built-up area, eligible is 0.0."""
    eligible = calculate_eligible_built_up_area(
        total_built_up_area=500.0,
        stilt_parking_area=300.0,
        basement_parking_area=200.0,
        balcony_area=0.0,
    )
    assert eligible == 0.0


def test_eligible_built_up_area_rejects_excessive_exclusions():
    """Excluded area exceeding total built-up area must be rejected."""
    with pytest.raises(ValueError, match="cannot exceed total built-up area"):
        calculate_eligible_built_up_area(
            total_built_up_area=500.0,
            stilt_parking_area=400.0,
            basement_parking_area=200.0,
        )


def test_eligible_built_up_area_rejects_negative_values():
    """Negative values in any area input must be rejected."""
    with pytest.raises(ValueError, match="Total built-up area cannot be negative"):
        calculate_eligible_built_up_area(total_built_up_area=-100)

    with pytest.raises(ValueError, match="Stilt parking area cannot be negative"):
        calculate_eligible_built_up_area(total_built_up_area=1000, stilt_parking_area=-50)

    with pytest.raises(ValueError, match="Basement parking area cannot be negative"):
        calculate_eligible_built_up_area(total_built_up_area=1000, basement_parking_area=-50)

    with pytest.raises(ValueError, match="Balcony area cannot be negative"):
        calculate_eligible_built_up_area(total_built_up_area=1000, balcony_area=-10)


def test_eligible_built_up_area_rejects_non_numeric_and_bool():
    """Non-numeric or boolean values must be rejected with TypeError."""
    with pytest.raises(TypeError, match="must be a number"):
        calculate_eligible_built_up_area(total_built_up_area="1000")  # type: ignore

    with pytest.raises(TypeError, match="must be a number"):
        calculate_eligible_built_up_area(total_built_up_area=True)  # type: ignore


# ==============================================================================
# 9. Premium FAR Tests (Task 2)
# ==============================================================================

def test_validate_premium_far_valid():
    """Valid premium FAR up to 0.5 on road >= 12m."""
    assert validate_premium_far(premium_far=0.3, road_width=12.0) == 0.3
    assert validate_premium_far(premium_far=0.5, road_width=15.0) == 0.5


def test_validate_premium_far_zero_allowed_any_road():
    """Zero premium FAR is always valid, even on narrow roads (< 12m)."""
    assert validate_premium_far(premium_far=0.0, road_width=9.0) == 0.0


def test_validate_premium_far_boundary_road_exactly_12m():
    """Exact boundary: Road width of exactly 12.0m is eligible for premium FAR."""
    assert validate_premium_far(premium_far=0.5, road_width=12.0) == 0.5


def test_validate_premium_far_boundary_max_0_5():
    """Exact boundary: Premium FAR of exactly 0.5 is permitted."""
    assert validate_premium_far(premium_far=0.5, road_width=18.0) == 0.5


def test_validate_premium_far_rejects_exceeding_0_5():
    """Premium FAR above 0.5 must be rejected."""
    with pytest.raises(ValueError, match="exceeds maximum allowed limit of 0.5"):
        validate_premium_far(premium_far=0.51, road_width=15.0)


def test_validate_premium_far_rejects_narrow_road():
    """Road width below 12m cannot receive premium FAR."""
    with pytest.raises(ValueError, match="at least 12 metres"):
        validate_premium_far(premium_far=0.2, road_width=11.99)


def test_validate_premium_far_rejects_negative():
    """Negative premium FAR must be rejected."""
    with pytest.raises(ValueError, match="Premium FAR cannot be negative"):
        validate_premium_far(premium_far=-0.1, road_width=15.0)


def test_premium_far_charges():
    """Verify residential (40%) and commercial (60%) charge calculations."""
    guidance = 10000.0  # currency per sq.m

    # Residential rate: 40% of 10,000 = 4,000 / sq.m
    res_rate = calculate_premium_far_rate("residential", guidance)
    assert res_rate == 4000.0

    # Commercial rate: 60% of 10,000 = 6,000 / sq.m
    comm_rate = calculate_premium_far_rate("commercial", guidance)
    assert comm_rate == 6000.0

    # Charge calculation: plot = 1000 sq.m, premium FAR = 0.5
    # Chargeable area = 0.5 * 1000 = 500 sq.m
    # Residential fee = 500 * 4000 = 2,000,000
    res_charge = calculate_premium_far_charge(
        premium_far=0.5,
        plot_area=1000.0,
        building_use="residential",
        guidance_value=guidance,
    )
    assert res_charge["chargeable_area"] == 500.0
    assert res_charge["rate_per_sqm"] == 4000.0
    assert res_charge["total_charge"] == 2000000.0


def test_premium_far_charge_flags_mixed_use_ambiguity():
    """Mixed use rate is unspecified in official rules; must raise clear ValueError."""
    with pytest.raises(ValueError, match="mixed_use.*not defined in official rules"):
        calculate_premium_far_rate("mixed_use", 10000.0)


# ==============================================================================
# 10. TDR FAR Tests (Task 3)
# ==============================================================================

def test_validate_tdr_far_valid():
    """Valid TDR FAR between 0.0 and 0.4."""
    assert validate_tdr_far(0.0) == 0.0
    assert validate_tdr_far(0.2) == 0.2
    assert validate_tdr_far(0.4) == 0.4


def test_validate_tdr_far_boundary_max_0_4():
    """Exact boundary: TDR FAR of exactly 0.4 is permitted."""
    assert validate_tdr_far(0.4) == 0.4


def test_validate_tdr_far_rejects_exceeding_0_4():
    """TDR FAR above 0.4 must be rejected."""
    with pytest.raises(ValueError, match="exceeds maximum allowed limit of 0.4"):
        validate_tdr_far(0.41)


def test_validate_tdr_far_rejects_negative():
    """Negative TDR FAR must be rejected."""
    with pytest.raises(ValueError, match="TDR FAR cannot be negative"):
        validate_tdr_far(-0.1)


# ==============================================================================
# 11. Combined Additional FAR & Cap Tests (Task 3)
# ==============================================================================

def test_final_permitted_far_within_cap():
    """Combined additional FAR within the 0.6 cap."""
    # Base 2.25, Premium 0.3, TDR 0.2 -> Combined = 0.5 <= 0.6 -> Final = 2.75
    final_far = calculate_final_permitted_far(
        base_far=2.25,
        premium_far=0.3,
        tdr_far=0.2,
        road_width=15.0,
    )
    assert final_far == 2.75


def test_final_permitted_far_boundary_exactly_0_6():
    """Exact boundary: Combined additional FAR of exactly 0.6 is allowed."""
    # Base 2.25, Premium 0.3, TDR 0.3 -> Combined = 0.6 -> Final = 2.85
    final_far = calculate_final_permitted_far(
        base_far=2.25,
        premium_far=0.3,
        tdr_far=0.3,
        road_width=15.0,
    )
    assert final_far == 2.85


def test_final_permitted_far_exceeding_cap_official_example():
    """Official edge case: Premium 0.5 + TDR 0.4 = 0.9 exceeds cap by 0.3.

    Must be rejected with ValueError stating the exact excess of 0.3.
    """
    with pytest.raises(ValueError, match=r"exceeds the maximum combined limit of 0.6 by 0.3"):
        calculate_final_permitted_far(
            base_far=1.75,
            premium_far=0.5,
            tdr_far=0.4,
            road_width=15.0,
        )


def test_final_permitted_far_exceeding_cap_slight_overage():
    """Combined additional FAR of 0.65 exceeds cap by 0.05."""
    with pytest.raises(ValueError, match=r"exceeds the maximum combined limit of 0.6 by 0.05"):
        calculate_final_permitted_far(
            base_far=2.25,
            premium_far=0.4,
            tdr_far=0.25,
            road_width=15.0,
        )


# ==============================================================================
# 12. Full Integration in validate_far (Task 1, 2, 3)
# ==============================================================================

def test_validate_far_full_integration_compliant():
    """Integration: Total area with exclusions + Base FAR from road width + Premium & TDR."""
    # Plot = 1000 sq.m, Road = 15m, Residential -> Base FAR = 2.25
    # Premium = 0.3, TDR = 0.2 -> Allowed FAR = 2.25 + 0.5 = 2.75
    # Total Built-up = 3100, Stilt = 200, Basement = 100, Balcony = 500 (10% = 50)
    # Eligible = 3100 - (200 + 100 + 50) = 2750 sq.m
    # Calculated FAR = 2750 / 1000 = 2.75 == 2.75 -> COMPLIANT (Exact boundary!)
    result = validate_far(
        plot_area=1000.0,
        total_built_up_area=3100.0,
        stilt_parking_area=200.0,
        basement_parking_area=100.0,
        balcony_area=500.0,
        building_use="residential",
        road_width=15.0,
        premium_far=0.3,
        tdr_far=0.2,
    )

    assert result["is_compliant"] is True
    assert result["eligible_built_up_area"] == 2750.0
    assert result["base_far"] == 2.25
    assert result["premium_far"] == 0.3
    assert result["tdr_far"] == 0.2
    assert result["allowed_far"] == 2.75
    assert result["calculated_far"] == 2.75
    assert "within the permitted limit" in result["message"]


def test_validate_far_full_integration_non_compliant():
    """Integration: Same setup but eligible area exceeds final permitted FAR."""
    # Eligible = 2800 / 1000 = 2.80 > 2.75 -> NON-COMPLIANT
    result = validate_far(
        plot_area=1000.0,
        eligible_built_up_area=2800.0,
        building_use="residential",
        road_width=15.0,
        premium_far=0.3,
        tdr_far=0.2,
    )

    assert result["is_compliant"] is False
    assert result["allowed_far"] == 2.75
    assert result["calculated_far"] == 2.8
    assert "exceeds the permitted limit" in result["message"]
