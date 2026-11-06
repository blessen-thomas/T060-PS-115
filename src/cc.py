"""Completion Certificate (CC) and Deviation Compounding Module for PS-115.

This module evaluates as-built construction deviations against approved plans
for building-plan approval completion certification.

Statutory Rules:
1. Built-Up Area Deviation:
   - deviation_pct = ((as_built_built_up - approved_built_up) / approved_built_up) * 100
   - deviation_pct <= 0.0%: No compounding fee (Rs 0.00).
   - 0.0% < deviation_pct <= 5.0%: Compounded at 2x development charge on excess area.
   - 5.0% < deviation_pct <= 10.0%: Compounded at 4x development charge on excess area.
   - deviation_pct > 10.0%: Non-compoundable -> CC_REFUSED.
2. Setback Deviation:
   - deviation_m <= 0.30 m: Compounded at Rs 10,000 per metre-side
     (fee = 10000.0 * deviation_m * sides_deviating).
   - deviation_m > 0.30 m: Non-compoundable -> CC_REFUSED.
3. Height Deviation:
   - As-built height exceeding approved height (height_deviation_m > 0.0):
     Height deviations are NEVER compounded -> CC_REFUSED.
4. Compounding Fees:
   - Rounded UP to the nearest Rs 10 (ceil(fee / 10) * 10).
   - Compounding fees apply only when CC is issued (CC_ISSUED). If CC is refused,
     compounding fees are reported as 0.00.
5. Decision Values:
   - Exactly CC_ISSUED or CC_REFUSED.

Output Schema for cc_decisions.csv:
   app_id,request_date,deviation_pct,area_compounding_fee,setback_compounding_fee,height_deviation_m,decision
"""

from __future__ import annotations

import math
from typing import Any

from src.fees import round_up_to_nearest_10


def _validate_numeric(value: Any, field_name: str, allow_zero: bool = True) -> float:
    """Validate numeric input and reject booleans and negative values."""
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


def calculate_built_up_deviation(
    approved_built_up_sqm: float,
    as_built_built_up_sqm: float,
) -> tuple[float, float]:
    """Calculate the excess built-up area and percentage deviation.

    Formula:
        excess_sqm = max(0.0, as_built - approved)
        deviation_pct = (excess_sqm / approved) * 100.0

    Returns:
        tuple[float, float]: (excess_sqm, deviation_pct) where deviation_pct
        is rounded to 2 decimal places.
    """
    approved = _validate_numeric(approved_built_up_sqm, "Approved built-up area", allow_zero=False)
    as_built = _validate_numeric(as_built_built_up_sqm, "As-built built-up area", allow_zero=True)

    if as_built <= approved:
        return 0.0, 0.0

    excess_sqm = as_built - approved
    raw_pct = (excess_sqm / approved) * 100.0
    return round(excess_sqm, 4), round(raw_pct, 2)


def calculate_area_compounding_fee(
    excess_built_up_sqm: float,
    deviation_pct: float,
    dev_charge_rate: float = 300.0,
) -> float:
    """Calculate compounding fee for built-up area deviation.

    Slabs:
        - deviation_pct <= 0.0%: Rs 0.0
        - 0.0% < deviation_pct <= 5.0%: 2x development charge on excess area.
        - 5.0% < deviation_pct <= 10.0%: 4x development charge on excess area.
        - deviation_pct > 10.0%: Non-compoundable (raises ValueError).

    Returns:
        float: Fee rounded UP to nearest Rs 10.
    """
    excess = _validate_numeric(excess_built_up_sqm, "Excess built-up area", allow_zero=True)
    pct = _validate_numeric(deviation_pct, "Deviation percentage", allow_zero=True)
    rate = _validate_numeric(dev_charge_rate, "Development charge rate", allow_zero=False)

    if excess <= 0.0 or pct <= 0.0:
        return 0.0

    # Tolerance up to exactly 5.00%
    if round(pct, 2) <= 5.00:
        multiplier = 2.0
    elif round(pct, 2) <= 10.00:
        multiplier = 4.0
    else:
        raise ValueError(
            f"Deviation {pct:.2f}% exceeds 10% maximum compounding ceiling; non-compoundable."
        )

    raw_fee = multiplier * rate * excess
    return round_up_to_nearest_10(raw_fee)


def calculate_setback_compounding_fee(
    deviation_m: float,
    sides_deviating: int,
    rate_per_metre_side: float = 10000.0,
) -> float:
    """Calculate compounding fee for setback deviations.

    Formula:
        If deviation_m <= 0.30 m:
            Fee = rate_per_metre_side * deviation_m * sides_deviating
        If deviation_m > 0.30 m:
            Non-compoundable (raises ValueError).

    Returns:
        float: Fee rounded UP to nearest Rs 10.
    """
    dev = _validate_numeric(deviation_m, "Setback deviation", allow_zero=True)
    if isinstance(sides_deviating, bool) or not isinstance(sides_deviating, int):
        raise TypeError("sides_deviating must be an integer.")
    if sides_deviating < 0:
        raise ValueError("sides_deviating cannot be negative.")

    if dev <= 0.0 or sides_deviating == 0:
        return 0.0

    if round(dev, 4) > 0.30:
        raise ValueError(
            f"Setback deviation {dev:.2f}m exceeds 0.30m maximum compounding tolerance."
        )

    rate = _validate_numeric(rate_per_metre_side, "Rate per metre-side", allow_zero=False)
    raw_fee = rate * dev * sides_deviating
    return round_up_to_nearest_10(raw_fee)


def evaluate_cc_request(
    app_id: str,
    request_date: str,
    approved_built_up_sqm: float,
    as_built_built_up_sqm: float,
    approved_height_m: float,
    as_built_height_m: float,
    setback_deviation_m: float = 0.0,
    sides_deviating: int = 0,
    dev_charge_rate: float = 300.0,
) -> dict:
    """Evaluate a Completion Certificate (CC) request and issue decision.

    Refusal Criteria:
        1. deviation_pct > 10.0% (area excess non-compoundable)
        2. height_deviation_m > 0.0 (height deviations never compoundable)
        3. setback_deviation_m > 0.30 (setback deviation non-compoundable)

    Returns:
        dict: Standard CC decision record matching cc_decisions.csv:
            - app_id: Application identifier
            - request_date: Date of CC request
            - deviation_pct: Area deviation % (2 decimals)
            - area_compounding_fee: Area compounding fee (Rs)
            - setback_compounding_fee: Setback compounding fee (Rs)
            - height_deviation_m: Height deviation in metres (2 decimals)
            - decision: 'CC_ISSUED' or 'CC_REFUSED'
    """
    clean_app_id = str(app_id).strip()
    clean_date = str(request_date).strip()

    # 1. Height deviation check
    appr_h = _validate_numeric(approved_height_m, "Approved building height", allow_zero=False)
    as_built_h = _validate_numeric(as_built_height_m, "As-built building height", allow_zero=False)
    height_diff = round(max(0.0, as_built_h - appr_h), 2)

    # 2. Area deviation check
    excess_sqm, dev_pct = calculate_built_up_deviation(approved_built_up_sqm, as_built_built_up_sqm)

    # 3. Setback deviation check
    sb_dev = _validate_numeric(setback_deviation_m, "Setback deviation", allow_zero=True)

    # 4. Determine decision
    is_refused = False
    refusal_reasons: list[str] = []

    if height_diff > 0.0:
        is_refused = True
        refusal_reasons.append(f"Height exceeded approved height by {height_diff:.2f}m")

    if round(dev_pct, 2) > 10.00:
        is_refused = True
        refusal_reasons.append(f"Area deviation {dev_pct:.2f}% exceeds 10% maximum compounding limit")

    if round(sb_dev, 4) > 0.30:
        is_refused = True
        refusal_reasons.append(f"Setback deviation {sb_dev:.2f}m exceeds 0.30m maximum tolerance")

    if is_refused:
        decision = "CC_REFUSED"
        area_fee = 0.0
        setback_fee = 0.0
    else:
        decision = "CC_ISSUED"
        area_fee = calculate_area_compounding_fee(excess_sqm, dev_pct, dev_charge_rate)
        setback_fee = calculate_setback_compounding_fee(sb_dev, sides_deviating)

    return {
        "app_id": clean_app_id,
        "request_date": clean_date,
        "deviation_pct": f"{dev_pct:.2f}",
        "area_compounding_fee": area_fee,
        "setback_compounding_fee": setback_fee,
        "height_deviation_m": f"{height_diff:.2f}",
        "decision": decision,
    }


def process_cc_commands(
    commands: list[str],
    applications: list[dict],
    floors_by_app: dict[str, list[dict]],
) -> list[dict]:
    """Extract and evaluate all CC_REQUEST commands from commands.txt."""
    apps_by_id = {str(a["app_id"]).strip(): a for a in applications}
    results: list[dict] = []

    for line in commands:
        line_clean = line.strip()
        if not line_clean.startswith("CC_REQUEST|"):
            continue

        parts = line_clean.split("|")
        app_id = parts[1].strip()
        req_date = parts[2].strip()
        as_built_bua = float(parts[3].strip())
        sb_dev = float(parts[4].strip())
        sides = int(parts[5].strip())
        as_built_h = float(parts[6].strip())

        app = apps_by_id[app_id]
        floors = floors_by_app[app_id]
        approved_bua = sum(float(f["built_up_sqm"]) for f in floors)
        approved_h = float(app["building_height_m"])
        use = str(app["proposed_use"]).strip().upper()

        # Development charge rate:
        # Commercial = 600, Residential = 300, Mixed = 400 (from floor breakdown)
        if use == "COMMERCIAL":
            dev_rate = 600.0
        elif use == "RESIDENTIAL":
            dev_rate = 300.0
        else:
            # Mixed use effective rate from floor areas
            comm_bua = sum(float(f["built_up_sqm"]) for f in floors if str(f.get("floor_use", "")).strip().upper() == "COMMERCIAL")
            other_bua = approved_bua - comm_bua
            tot_dev = (comm_bua * 600.0) + (other_bua * 300.0)
            dev_rate = tot_dev / approved_bua if approved_bua > 0 else 300.0

        decision_row = evaluate_cc_request(
            app_id=app_id,
            request_date=req_date,
            approved_built_up_sqm=approved_bua,
            as_built_built_up_sqm=as_built_bua,
            approved_height_m=approved_h,
            as_built_height_m=as_built_h,
            setback_deviation_m=sb_dev,
            sides_deviating=sides,
            dev_charge_rate=dev_rate,
        )
        results.append(decision_row)

    return results
