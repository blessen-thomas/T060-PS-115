"""End-to-End Command Runner and CSV Output Generation Pipeline for PS-115.

This module executes the official command pipeline from commands.txt strictly
in source order and generates the four mandatory municipal output files:
1. validation_report.csv: Plan validation results and violations in precedence order.
2. fee_demand.csv: Official fee demand breakdown for compliant/compoundable plans.
3. workflow.csv: Stage transition logs, working day counts, and deemed approvals.
4. cc_decisions.csv: Completion certificate decisions and deviation compounding fees.

Statutory Precedence Order:
    ZONING_USE -> FAR (BASE, PREMIUM, TDR, CAP, ACHIEVED) -> GROUND_COVERAGE
    -> SETBACKS (FRONT, SIDE1, SIDE2, REAR) -> HEIGHT_LIMIT -> PARKING
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys
from typing import Any

from src.cc import evaluate_cc_request
from src.data_loader import load_data_pack
from src.far import get_base_far
from src.fees import calculate_fee_demand
from src.rules import (
    check_all_setbacks,
    check_building_height,
    check_ground_coverage,
    check_parking,
    check_zoning_use,
)
from src.workflow import ApplicationWorkflow

# Canonical statutory rule evaluation precedence
RULE_PRECEDENCE = [
    "ZONING_USE",
    "FAR_BASE",
    "FAR_PREMIUM",
    "FAR_TDR",
    "FAR_CAP",
    "FAR_ACHIEVED",
    "GROUND_COVERAGE",
    "SETBACK_FRONT",
    "SETBACK_SIDE1",
    "SETBACK_SIDE2",
    "SETBACK_REAR",
    "HEIGHT_LIMIT",
    "PARKING",
]


def validate_application(
    app: dict,
    floors: list[dict],
    zones: dict[str, dict],
    setback_table: list[dict],
    coverage_table: list[dict],
) -> list[dict]:
    """Evaluate all statutory municipal compliance rules in exact precedence order.

    Returns:
        list[dict]: List of non-compliant check results (empty if plan is 100% compliant).
    """
    violations: list[dict] = []

    # 1. Zoning Permitted Use
    zv = check_zoning_use(app["zone_id"], app["proposed_use"], zones)
    if not zv["passed"]:
        violations.append(zv)

    # 2. FAR & Eligible Exclusions
    total_bua = sum(float(f["built_up_sqm"]) for f in floors)
    parking_bua = sum(float(f["built_up_sqm"]) for f in floors if str(f.get("floor_use", "")).strip().upper() == "PARKING")
    comm_bua = sum(float(f["built_up_sqm"]) for f in floors if str(f.get("floor_use", "")).strip().upper() == "COMMERCIAL")
    balcony_bua = sum(float(f.get("balcony_sqm", 0.0)) for f in floors)
    eligible_bua = total_bua - parking_bua - (0.10 * balcony_bua)

    use_for_far = "mixed_use" if str(app["proposed_use"]).strip().lower() in ("mixed", "mixed_use") else str(app["proposed_use"]).strip().lower()
    base_far = get_base_far(use_for_far, float(app["road_width_m"]))

    prem_req = float(app.get("premium_far_requested", 0.0))
    if prem_req > 0.0:
        if float(app["road_width_m"]) < 12.0:
            violations.append({
                "passed": False,
                "rule_id": "FAR_PREMIUM",
                "check": "Premium FAR road width requirement (>= 12.0m)",
                "required": ">= 12.00m",
                "proposed": f"{float(app['road_width_m']):.2f}m",
                "compoundable": False,
            })
        elif prem_req > 0.50:
            violations.append({
                "passed": False,
                "rule_id": "FAR_PREMIUM",
                "check": "Premium FAR limit (max 0.50)",
                "required": "<= 0.50",
                "proposed": f"{prem_req:.2f}",
                "compoundable": False,
            })

    tdr_req = float(app.get("tdr_far_requested", 0.0))
    if tdr_req > 0.40:
        violations.append({
            "passed": False,
            "rule_id": "FAR_TDR",
            "check": "TDR FAR limit (max 0.40)",
            "required": "<= 0.40",
            "proposed": f"{tdr_req:.2f}",
            "compoundable": False,
        })

    if (prem_req + tdr_req) > 0.60:
        violations.append({
            "passed": False,
            "rule_id": "FAR_CAP",
            "check": "Combined additional FAR cap (Premium + TDR <= 0.60)",
            "required": "<= 0.60",
            "proposed": f"{prem_req + tdr_req:.2f}",
            "compoundable": False,
        })

    allowed_additional = min(0.60, prem_req + tdr_req) if float(app["road_width_m"]) >= 12.0 or prem_req == 0.0 else min(0.60, tdr_req)
    total_allowed_far = base_far + allowed_additional
    far_achieved = eligible_bua / float(app["plot_area_sqm"])
    if far_achieved > total_allowed_far:
        violations.append({
            "passed": False,
            "rule_id": "FAR_ACHIEVED",
            "check": f"Permitted FAR for road {float(app['road_width_m']):.2f}m",
            "required": f"{total_allowed_far:.2f}",
            "proposed": f"{far_achieved:.4f}",
            "compoundable": False,
        })

    # 3. Ground Coverage
    cv = check_ground_coverage(float(app["ground_footprint_sqm"]), float(app["plot_area_sqm"]), coverage_table)
    if not cv["passed"]:
        violations.append(cv)

    # 4. Setbacks
    sb_list = check_all_setbacks(app, setback_table)
    for sb in sb_list:
        if not sb["passed"]:
            violations.append(sb)

    # 5. Building Height Limit
    hv = check_building_height(
        proposed_height_m=float(app["building_height_m"]),
        road_width_m=float(app["road_width_m"]),
        zone_id=app["zone_id"],
        zones=zones,
        setback_table=setback_table,
        is_corner_plot=bool(app.get("is_corner_plot", False)),
        second_road_width_m=float(app["second_road_width_m"]) if app.get("second_road_width_m") else None,
    )
    if not hv["passed"]:
        violations.append(hv)

    # 6. Parking
    pv = check_parking(
        parking_proposed=int(app["parking_proposed"]),
        units_carpet_above_100=int(app.get("units_carpet_above_100", 0)),
        units_carpet_upto_100=int(app.get("units_carpet_upto_100", 0)),
        commercial_built_up_sqm=comm_bua,
    )
    if not pv["passed"]:
        violations.append(pv)

    # Sort strictly by statutory precedence
    def get_precedence(v: dict) -> int:
        rid = v.get("rule_id", "")
        return RULE_PRECEDENCE.index(rid) if rid in RULE_PRECEDENCE else 999

    violations.sort(key=get_precedence)
    return violations


def generate_validation_report(
    applications: list[dict],
    floors_by_app: dict[str, list[dict]],
    data_pack: dict[str, Any],
) -> list[dict]:
    """Generate the full validation report records.

    Rules:
        - Sorted by app_id, then rule precedence.
        - Exactly one row per violation for non-compliant plans.
        - Compliant plans emit exactly one row with rule_id='NONE'.
    """
    zones = data_pack["zones"]
    setback_table = data_pack["setback_table"]
    coverage_table = data_pack["coverage_table"]

    report_rows: list[dict] = []
    sorted_apps = sorted(applications, key=lambda a: a["app_id"])

    for app in sorted_apps:
        aid = app["app_id"]
        fl = floors_by_app.get(aid, [])
        violations = validate_application(app, fl, zones, setback_table, coverage_table)

        if not violations:
            report_rows.append({
                "app_id": aid,
                "rule_id": "NONE",
                "check": "No violations",
                "required": "-",
                "proposed": "-",
                "compoundable": False,
            })
        else:
            for item in violations:
                report_rows.append({
                    "app_id": aid,
                    "rule_id": item["rule_id"],
                    "check": item["check"],
                    "required": str(item["required"]),
                    "proposed": str(item["proposed"]),
                    "compoundable": bool(item.get("compoundable", False)),
                })

    return report_rows


def write_csv(filepath: pathlib.Path | str, fieldnames: list[str], rows: list[dict]) -> None:
    """Write rows to a CSV file with explicit headers and LF line endings."""
    p = pathlib.Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="\n", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def run_command_pipeline(
    commands_path: pathlib.Path | str,
    data_dir: pathlib.Path | str,
    output_dir: pathlib.Path | str | None = None,
    print_output: bool = False,
) -> dict[str, list[dict]]:
    """Execute the command pipeline strictly in file order and generate all outputs."""
    p_cmd = pathlib.Path(commands_path)
    p_data = pathlib.Path(data_dir)

    data_pack = load_data_pack(p_data)
    apps_by_id = {str(a["app_id"]).strip(): a for a in data_pack["applications"]}
    floors_by_app = data_pack["floors_by_app"]
    holidays = data_pack["holidays"]

    # 1. Compile validation results
    validation_rows = generate_validation_report(data_pack["applications"], floors_by_app, data_pack)
    validation_by_app: dict[str, list[dict]] = {}
    for row in validation_rows:
        aid = row["app_id"]
        validation_by_app.setdefault(aid, []).append(row)

    # 2. State trackers
    workflows: dict[str, ApplicationWorkflow] = {aid: ApplicationWorkflow(aid, holidays) for aid in apps_by_id}
    fee_demand_rows: list[dict] = []
    cc_decision_rows: list[dict] = []

    # 3. Process commands line by line
    raw_lines = p_cmd.read_text(encoding="utf-8").splitlines()

    for line in raw_lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue

        parts = line_clean.split("|")
        cmd = parts[0].strip()
        aid = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "SUBMIT":
            submit_date = parts[2].strip()
            wf = workflows[aid]
            wf.submit(submit_date)

            # Issue fee demand if no non-compoundable violations exist
            v_rows = validation_by_app.get(aid, [])
            fatal_exist = any(r["rule_id"] != "NONE" and not r.get("compoundable", False) for r in v_rows)
            if not fatal_exist:
                # Calculate parking shortfall if applicable
                app = apps_by_id[aid]
                fl = floors_by_app[aid]
                comm_bua = sum(float(f["built_up_sqm"]) for f in fl if str(f.get("floor_use", "")).strip().upper() == "COMMERCIAL")
                u_gt = int(app.get("units_carpet_above_100", 0))
                u_le = int(app.get("units_carpet_upto_100", 0))
                req_cars = (u_gt * 1.0) + (u_le * 0.5) + (comm_bua / 50.0)
                shortfall = max(0.0, req_cars - int(app["parking_proposed"]))

                demand = calculate_fee_demand(app, fl, parking_shortfall_cars=shortfall)
                if demand is not None:
                    fee_demand_rows.append(demand)

        elif cmd == "PRINT_VALIDATION":
            if print_output:
                print(f"[VALIDATION] {aid}: {len(validation_by_app.get(aid, []))} row(s)")

        elif cmd == "FEE_PAYMENT":
            pay_date = parts[2].strip()
            amount = float(parts[3].strip())
            challan = parts[4].strip() if len(parts) > 4 else ""
            workflows[aid].pay_fees(pay_date, amount, challan)

        elif cmd == "STAGE_RESULT":
            stage = parts[2].strip()
            r_date = parts[3].strip()
            result = parts[4].strip()
            workflows[aid].record_stage_result(stage, r_date, result)

        elif cmd == "QUERY_RESPONSE":
            resp_date = parts[2].strip()
            workflows[aid].respond_to_query(resp_date)

        elif cmd == "REVIVE":
            req_date = parts[2].strip()
            workflows[aid].lapse(req_date)
            workflows[aid].revive(req_date)

        elif cmd == "COMMENCEMENT":
            c_date = parts[2].strip()
            workflows[aid].report_commencement(c_date)

        elif cmd == "REVALIDATION_FEE":
            p_date = parts[2].strip()
            amt = float(parts[3].strip())
            workflows[aid].pay_revalidation_fee(p_date, amt)

        elif cmd == "EXTENSION":
            e_date = parts[2].strip()
            workflows[aid].request_extension(e_date)

        elif cmd == "CC_REQUEST":
            r_date = parts[2].strip()
            as_built_bua = float(parts[3].strip())
            sb_dev = float(parts[4].strip())
            sides = int(parts[5].strip())
            as_built_h = float(parts[6].strip())

            app = apps_by_id[aid]
            fl = floors_by_app[aid]
            approved_bua = sum(float(f["built_up_sqm"]) for f in fl)
            approved_h = float(app["building_height_m"])
            use = str(app["proposed_use"]).strip().upper()

            if use == "COMMERCIAL":
                dev_rate = 600.0
            elif use == "RESIDENTIAL":
                dev_rate = 300.0
            else:
                comm_bua = sum(float(f["built_up_sqm"]) for f in fl if str(f.get("floor_use", "")).strip().upper() == "COMMERCIAL")
                other_bua = approved_bua - comm_bua
                tot_dev = (comm_bua * 600.0) + (other_bua * 300.0)
                dev_rate = tot_dev / approved_bua if approved_bua > 0 else 300.0

            dec = evaluate_cc_request(
                app_id=aid,
                request_date=r_date,
                approved_built_up_sqm=approved_bua,
                as_built_built_up_sqm=as_built_bua,
                approved_height_m=approved_h,
                as_built_height_m=as_built_h,
                setback_deviation_m=sb_dev,
                sides_deviating=sides,
                dev_charge_rate=dev_rate,
            )
            cc_decision_rows.append(dec)

        elif cmd == "PRINT_CC":
            if print_output:
                print(f"[CC] {aid}")

        elif cmd == "PRINT_FEE_DEMAND":
            if print_output:
                print(f"[FEE_DEMAND] {aid}")

        elif cmd == "PRINT_WORKFLOW":
            as_of = parts[2].strip() if len(parts) > 2 else "2026-10-31"
            workflows[aid].evaluate_as_of(as_of)

    # 4. Compile all workflow transitions
    workflow_rows: list[dict] = []
    for aid in sorted(workflows.keys()):
        workflow_rows.extend(workflows[aid].transitions)

    # 5. Export CSV files if output_dir provided
    if output_dir is not None:
        p_out = pathlib.Path(output_dir)
        p_out.mkdir(parents=True, exist_ok=True)

        write_csv(
            p_out / "validation_report.csv",
            ["app_id", "rule_id", "check", "required", "proposed", "compoundable"],
            validation_rows,
        )

        write_csv(
            p_out / "fee_demand.csv",
            [
                "app_id",
                "built_up_sqm",
                "far_area_sqm",
                "far_achieved",
                "far_allowed",
                "scrutiny_fee",
                "development_charge",
                "premium_far_fee",
                "betterment_levy",
                "labour_cess",
                "parking_shortfall_fee",
                "total_fee",
            ],
            fee_demand_rows,
        )

        write_csv(
            p_out / "workflow.csv",
            [
                "app_id",
                "stage",
                "entered_date",
                "exited_date",
                "working_days",
                "clock_stopped_days",
                "status_after",
                "deemed_approval_date",
            ],
            workflow_rows,
        )

        write_csv(
            p_out / "cc_decisions.csv",
            [
                "app_id",
                "request_date",
                "deviation_pct",
                "area_compounding_fee",
                "setback_compounding_fee",
                "height_deviation_m",
                "decision",
            ],
            cc_decision_rows,
        )

    return {
        "validation_report": validation_rows,
        "fee_demand": fee_demand_rows,
        "workflow": workflow_rows,
        "cc_decisions": cc_decision_rows,
    }


def main() -> None:
    """CLI entrypoint for processing commands.txt and exporting all reports."""
    parser = argparse.ArgumentParser(description="PS-115 Municipal Engine Command Pipeline Runner")
    parser.add_argument("commands", nargs="?", default="data/commands.txt", help="Path to commands.txt")
    parser.add_argument("--data-dir", default="data", help="Directory holding municipal input CSV tables")
    parser.add_argument("--output-dir", default=".", help="Directory to export the 4 output CSV files")
    parser.add_argument("--verbose", action="store_true", help="Print command processing progress")

    args = parser.parse_args()
    results = run_command_pipeline(
        commands_path=args.commands,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        print_output=args.verbose,
    )

    print(f"Pipeline executed successfully.")
    print(f"  validation_report.csv : {len(results['validation_report'])} rows")
    print(f"  fee_demand.csv        : {len(results['fee_demand'])} rows")
    print(f"  workflow.csv          : {len(results['workflow'])} rows")
    print(f"  cc_decisions.csv      : {len(results['cc_decisions'])} rows")


if __name__ == "__main__":
    main()
