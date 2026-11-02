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
from src.far import calculate_far, validate_far


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
