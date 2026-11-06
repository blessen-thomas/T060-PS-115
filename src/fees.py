"""Municipal Fee Engine and Demand Calculation Module for PS-115.

This module implements the calculation of all municipal fees required for
building-plan approval, following the official fee schedule and verified
sample data pack.

Official Fee Schedule:
1. Scrutiny Fee:
   - Rate: Rs 20.00 per sq.m of total built-up area.
   - Minimum: Rs 2,000.00.
2. Development Charge:
   - Pure Residential: Rs 300.00 per sq.m of total built-up area.
   - Pure Commercial: Rs 600.00 per sq.m of total built-up area.
   - Mixed-Use: Commercial floor areas at Rs 600.00/sq.m; residential and
     parking floor areas at Rs 300.00/sq.m (verified from floor-level audit).
3. Premium FAR Fee:
   - Roads >= 12m only.
   - Chargeable Area: premium_far_requested * plot_area_sqm.
   - Rate:
     - Commercial: 60% of plot guidance value per sq.m.
     - Residential: 40% of plot guidance value per sq.m.
     - Mixed-Use: 40% of plot guidance value per sq.m (evidence-based interpretation
       derived from 100% match across official sample payment records).
4. Betterment Levy:
   - Applicable only for plots converted from agricultural use (agri_converted == True).
   - Rate: 2% of total plot guidance value (0.02 * plot_area_sqm * guidance_value_per_sqm).
5. Labour Cess:
   - Rate: 1% of estimated construction cost.
   - Construction cost: Rs 1,800.00 per sq.ft (1 sq.m = 10.7639 sq.ft).
6. Parking Shortfall Fee:
   - Applicable for permitted parking shortfall (up to 20%): Rs 2,00,000.00 per missing car.

Rounding Rule:
- Every individual fee component is rounded UP to the nearest Rs 10 (ceil(amount / 10) * 10).
- total_fee is the exact sum of these individually rounded components.

Gating Rule:
- Fees are calculated ONLY if there are no non-compoundable violations.
  If fatal violations exist, fee demand is refused.
"""

from __future__ import annotations

import math
from typing import Any

from src.far import (
    calculate_eligible_built_up_area,
    calculate_far,
    calculate_final_permitted_far,
    get_base_far,
)


def _validate_numeric(value: Any, field_name: str, allow_zero: bool = True) -> float:
    """Validate numeric input and reject booleans, NaN, and negative numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number (int or float).")
    val_float = float(value)
    if math.isnan(val_float) or math.isinf(val_float):
        raise ValueError(f"{field_name} must be a finite number.")
    if allow_zero:
        if val_float < 0:
            raise ValueError(f"{field_name} cannot be negative.")
    else:
        if val_float <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")
    return val_float


def round_up_to_nearest_10(amount: float) -> float:
    """Round an amount UP to the nearest Rs 10 as specified by municipal rules.

    Examples:
        5040.0 -> 5040.0
        13489.8 -> 13490.0
        48825.05 -> 48830.0
    """
    val = _validate_numeric(amount, "Amount", allow_zero=True)
    if val <= 0.0:
        return 0.0
    return float(math.ceil(val / 10.0) * 10)


def calculate_scrutiny_fee(
    total_built_up_sqm: float,
    rate_per_sqm: float = 20.0,
    min_fee: float = 2000.0,
) -> float:
    """Calculate the scrutiny fee for plan verification.

    Formula:
        Raw Scrutiny Fee = max(min_fee, total_built_up_sqm * rate_per_sqm)
        Rounded UP to the nearest Rs 10.
    """
    bua = _validate_numeric(total_built_up_sqm, "Total built-up area", allow_zero=True)
    rate = _validate_numeric(rate_per_sqm, "Rate per sq.m", allow_zero=False)
    minimum = _validate_numeric(min_fee, "Minimum scrutiny fee", allow_zero=True)

    raw_fee = max(minimum, bua * rate)
    return round_up_to_nearest_10(raw_fee)


def calculate_development_charge(
    proposed_use: str,
    total_built_up_sqm: float,
    floors_data: list[dict] | None = None,
) -> float:
    """Calculate the development charge based on building use and floor areas.

    Rates:
        - Pure RESIDENTIAL: Rs 300 / sq.m across all floors.
        - Pure COMMERCIAL: Rs 600 / sq.m across all floors.
        - MIXED: Uses floor-level data from floors.csv:
          - Commercial floors: Rs 600 / sq.m
          - Non-commercial floors (residential, parking, stilt, basement): Rs 300 / sq.m

    Rounded UP to the nearest Rs 10.
    """
    if not isinstance(proposed_use, str):
        raise TypeError("proposed_use must be a string.")

    norm_use = proposed_use.strip().upper().replace(" ", "_").replace("-", "_")
    bua = _validate_numeric(total_built_up_sqm, "Total built-up area", allow_zero=True)

    if norm_use == "COMMERCIAL":
        raw_charge = bua * 600.0
    elif norm_use == "RESIDENTIAL":
        raw_charge = bua * 300.0
    elif norm_use in ("MIXED", "MIXED_USE"):
        if floors_data is None:
            raise ValueError("floors_data is required for mixed-use development charge calculation.")
        comm_bua = 0.0
        for floor in floors_data:
            floor_use = str(floor.get("floor_use", "")).strip().upper()
            fl_bua = _validate_numeric(floor.get("built_up_sqm", 0.0), "Floor built-up area", allow_zero=True)
            if floor_use == "COMMERCIAL":
                comm_bua += fl_bua
        other_bua = max(0.0, bua - comm_bua)
        raw_charge = (comm_bua * 600.0) + (other_bua * 300.0)
    else:
        raise ValueError(f"Unsupported proposed_use for development charge: {proposed_use!r}")

    return round_up_to_nearest_10(raw_charge)


def calculate_premium_far_fee(
    premium_far_requested: float,
    plot_area_sqm: float,
    guidance_value_per_sqm: float,
    proposed_use: str,
) -> float:
    """Calculate the premium FAR purchase fee.

    Formula:
        Chargeable Area = premium_far_requested * plot_area_sqm
        Charge = Chargeable Area * guidance_value_per_sqm * rate_percentage
        Where:
            Commercial: 60% (0.60)
            Residential: 40% (0.40)
            Mixed-Use: 40% (0.40) [Evidence-based interpretation from 27-payment official audit]

    Rounded UP to the nearest Rs 10.
    """
    prem_far = _validate_numeric(premium_far_requested, "Premium FAR requested", allow_zero=True)
    if prem_far <= 0.0:
        return 0.0

    plot_area = _validate_numeric(plot_area_sqm, "Plot area", allow_zero=False)
    guidance_val = _validate_numeric(guidance_value_per_sqm, "Guidance value per sq.m", allow_zero=True)

    if not isinstance(proposed_use, str):
        raise TypeError("proposed_use must be a string.")

    norm_use = proposed_use.strip().upper().replace(" ", "_").replace("-", "_")
    if norm_use == "COMMERCIAL":
        rate = 0.60
    elif norm_use in ("RESIDENTIAL", "MIXED", "MIXED_USE"):
        rate = 0.40
    else:
        raise ValueError(f"Unsupported proposed_use for premium FAR fee: {proposed_use!r}")

    chargeable_area = prem_far * plot_area
    raw_charge = chargeable_area * guidance_val * rate
    return round_up_to_nearest_10(raw_charge)


def calculate_betterment_levy(
    agri_converted: bool,
    plot_area_sqm: float,
    guidance_value_per_sqm: float,
    rate_pct: float = 2.0,
) -> float:
    """Calculate betterment levy for agricultural-converted land.

    Formula:
        If agri_converted is True:
            2% of total plot guidance value = 0.02 * (plot_area_sqm * guidance_value_per_sqm)
        Else:
            0.0

    Rounded UP to the nearest Rs 10.
    """
    if not isinstance(agri_converted, bool):
        raise TypeError("agri_converted must be a boolean.")

    if not agri_converted:
        return 0.0

    plot_area = _validate_numeric(plot_area_sqm, "Plot area", allow_zero=False)
    guidance_val = _validate_numeric(guidance_value_per_sqm, "Guidance value per sq.m", allow_zero=True)
    pct = _validate_numeric(rate_pct, "Betterment levy percentage", allow_zero=False)

    raw_fee = (pct / 100.0) * (plot_area * guidance_val)
    return round_up_to_nearest_10(raw_fee)


def calculate_labour_cess(
    total_built_up_sqm: float,
    cost_per_sqft: float = 1800.0,
    sqft_per_sqm: float = 10.7639,
    cess_pct: float = 1.0,
) -> float:
    """Calculate the 1% labour welfare cess on estimated construction cost.

    Formula:
        Estimated Construction Cost = total_built_up_sqm * 10.7639 * Rs 1,800.00
        Labour Cess = 1% of Construction Cost
        Rounded UP to the nearest Rs 10.
    """
    bua = _validate_numeric(total_built_up_sqm, "Total built-up area", allow_zero=True)
    cost = _validate_numeric(cost_per_sqft, "Construction cost per sq.ft", allow_zero=False)
    conversion = _validate_numeric(sqft_per_sqm, "Square feet per square metre", allow_zero=False)
    pct = _validate_numeric(cess_pct, "Cess percentage", allow_zero=False)

    construction_cost = bua * conversion * cost
    raw_cess = (pct / 100.0) * construction_cost
    return round_up_to_nearest_10(raw_cess)


def calculate_parking_shortfall_fee(
    parking_shortfall_cars: float,
    fee_per_car: float = 200000.0,
) -> float:
    """Calculate fee for allowable parking shortfall (up to 20%).

    Formula:
        Fee = parking_shortfall_cars * Rs 2,00,000.00
        Rounded UP to the nearest Rs 10.
    """
    shortfall = _validate_numeric(parking_shortfall_cars, "Parking shortfall cars", allow_zero=True)
    if shortfall <= 0.0:
        return 0.0

    rate = _validate_numeric(fee_per_car, "Fee per car", allow_zero=False)
    raw_fee = shortfall * rate
    return round_up_to_nearest_10(raw_fee)


def calculate_fee_demand(
    application: dict,
    floors: list[dict],
    parking_shortfall_cars: float = 0.0,
    validation_results: list[dict] | None = None,
) -> dict | None:
    """Assemble the complete municipal fee demand for an application.

    Gating Precondition:
        If validation_results contains any non-compoundable violation,
        no fee demand is generated and this function returns None.

    Output Schema (matches fee_demand.csv exactly):
        - app_id: Application identifier string
        - built_up_sqm: Total built-up area across all floors (sq.m)
        - far_area_sqm: Eligible built-up area for FAR calculation (sq.m)
        - far_achieved: Achieved FAR (far_area_sqm / plot_area_sqm)
        - far_allowed: Total permitted FAR (base + premium + TDR)
        - scrutiny_fee: Scrutiny fee (Rs)
        - development_charge: Development charge (Rs)
        - premium_far_fee: Premium FAR fee (Rs)
        - betterment_levy: Betterment levy (Rs)
        - labour_cess: Labour welfare cess (Rs)
        - parking_shortfall_fee: Parking shortfall fee (Rs)
        - total_fee: Total fee payable (Rs)

    Args:
        application: Dictionary of application fields from applications.csv.
        floors: List of floor dictionaries from floors.csv for this application.
        parking_shortfall_cars: Number of missing parking bays (if <= 20% allowed shortfall).
        validation_results: Optional list of validation result dicts to enforce gating.

    Returns:
        dict: Structured fee demand record, or None if gating fails.
    """
    # 1. Gating check: Refuse fee demand if any non-compoundable violation exists
    if validation_results is not None:
        for res in validation_results:
            if not res.get("passed", True) and not res.get("compoundable", False):
                return None

    app_id = str(application["app_id"]).strip()
    proposed_use = str(application["proposed_use"]).strip()
    plot_area = _validate_numeric(application["plot_area_sqm"], "Plot area", allow_zero=False)
    road_width = _validate_numeric(application["road_width_m"], "Road width", allow_zero=False)
    guidance_val = _validate_numeric(application["guidance_value_per_sqm"], "Guidance value", allow_zero=True)
    agri_converted = bool(str(application.get("agri_converted", "")).strip().lower() in ("true", "1", "yes"))
    prem_far_req = _validate_numeric(application.get("premium_far_requested", 0.0), "Premium FAR requested", allow_zero=True)
    tdr_far_req = _validate_numeric(application.get("tdr_far_requested", 0.0), "TDR FAR requested", allow_zero=True)

    # 2. Compute floor areas and FAR metrics
    total_bua = sum(float(f["built_up_sqm"]) for f in floors)
    parking_bua = sum(float(f["built_up_sqm"]) for f in floors if str(f.get("floor_use", "")).strip().upper() == "PARKING")
    total_balcony = sum(float(f.get("balcony_sqm", 0.0)) for f in floors)

    # Deduct 100% parking and 10% balcony
    eligible_bua = round(total_bua - parking_bua - (0.10 * total_balcony), 4)
    far_achieved = calculate_far(plot_area, eligible_bua)

    # Base and final allowed FAR
    use_for_far = "mixed_use" if proposed_use.lower() in ("mixed", "mixed_use") else proposed_use.lower()
    base_far = get_base_far(use_for_far, road_width)
    far_allowed = calculate_final_permitted_far(
        base_far=base_far,
        premium_far=prem_far_req,
        tdr_far=tdr_far_req,
        road_width=road_width,
    )

    # 3. Calculate all individual fee components
    scrutiny = calculate_scrutiny_fee(total_bua)
    dev_charge = calculate_development_charge(proposed_use, total_bua, floors)
    prem_fee = calculate_premium_far_fee(prem_far_req, plot_area, guidance_val, proposed_use)
    betterment = calculate_betterment_levy(agri_converted, plot_area, guidance_val)
    cess = calculate_labour_cess(total_bua)
    park_fee = calculate_parking_shortfall_fee(parking_shortfall_cars)

    total_fee = scrutiny + dev_charge + prem_fee + betterment + cess + park_fee

    return {
        "app_id": app_id,
        "built_up_sqm": round(total_bua, 2),
        "far_area_sqm": round(eligible_bua, 2),
        "far_achieved": round(far_achieved, 4),
        "far_allowed": round(far_allowed, 4),
        "scrutiny_fee": scrutiny,
        "development_charge": dev_charge,
        "premium_far_fee": prem_fee,
        "betterment_levy": betterment,
        "labour_cess": cess,
        "parking_shortfall_fee": park_fee,
        "total_fee": total_fee,
    }
