"""Municipal Workflow Engine and Application Lifecycle Module for PS-115.

This module models the statutory approval workflow, stage transitions, working-day
and holiday calendars, deemed approval logic, query pauses, lapses, one-time revival,
and commencement/extension tracking.

Statutory Stages:
    SUBMITTED -> SCRUTINY (7 days) -> SITE_INSPECTION (10 days) -> TECHNICAL (15 days) -> APPROVED / QUERY

Statutory Business Rules:
1. Workflow Timer:
   - Starts on the NEXT working day after municipal fee payment.
   - Working days are Monday through Friday, excluding public holidays from holidays.csv.
   - If fees are never paid, the workflow timer never starts.
2. Deemed Approval:
   - If cumulative running working days exceed 45 working days (i.e. on the 46th working day),
     the application is DEEMED_APPROVED, provided no violations were listed at scrutiny.
3. Query and Clock Pause:
   - A QUERY issued at TECHNICAL stops the workflow timer on that date.
   - Applicant must respond within 30 calendar days.
   - If responded in time, the clock resumes and query days are excluded from the 45 working days.
4. Lapse & Revival:
   - If query response is not submitted within 30 calendar days, the application becomes LAPSED.
   - A lapsed application may be revived ONCE within 60 calendar days of lapse by paying
     a revival fee equal to 25% of the scrutiny fee.
   - Once revived, applicant can submit query response and proceed.
5. Commencement & Validity:
   - Approval is valid for 2 years.
   - Commencement must be reported within 6 calendar months of approval; otherwise status
     becomes SUSPENDED. Revalidation costs Rs 5,000.
   - Approval extension: one-time 1-year extension at 10% of original fees. Second extension is REJECTED.

Output Schema for workflow.csv:
    app_id,stage,entered_date,exited_date,working_days,clock_stopped_days,status_after,deemed_approval_date
"""

from __future__ import annotations

import datetime
from typing import Any


def parse_date(date_val: str | datetime.date) -> datetime.date:
    """Parse an ISO 8601 date string (YYYY-MM-DD) or return datetime.date."""
    if isinstance(date_val, datetime.date):
        return date_val
    if isinstance(date_val, str):
        clean_str = date_val.strip()
        return datetime.date.fromisoformat(clean_str)
    raise TypeError(f"Expected str or datetime.date, got {type(date_val).__name__}")


def format_date(date_val: datetime.date | None) -> str:
    """Format datetime.date to YYYY-MM-DD or return '-' if None."""
    if date_val is None:
        return "-"
    return date_val.isoformat()


def is_working_day(date_val: datetime.date | str, holidays: set[str] | list[str]) -> bool:
    """Check if a date is a municipal working day (Mon-Fri and not a holiday)."""
    d = parse_date(date_val)
    if d.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return False
    d_str = d.isoformat()
    return d_str not in holidays


def get_next_working_day(date_val: datetime.date | str, holidays: set[str] | list[str]) -> datetime.date:
    """Get the next working day strictly following date_val."""
    cur = parse_date(date_val) + datetime.timedelta(days=1)
    while not is_working_day(cur, holidays):
        cur += datetime.timedelta(days=1)
    return cur


def count_working_days(
    start_date: datetime.date | str,
    end_date: datetime.date | str,
    holidays: set[str] | list[str],
    inclusive_start: bool = False,
    inclusive_end: bool = True,
) -> int:
    """Count municipal working days between start_date and end_date."""
    d_start = parse_date(start_date)
    d_end = parse_date(end_date)
    if d_start > d_end:
        return 0

    cur = d_start if inclusive_start else d_start + datetime.timedelta(days=1)
    target = d_end if inclusive_end else d_end - datetime.timedelta(days=1)

    count = 0
    while cur <= target:
        if is_working_day(cur, holidays):
            count += 1
        cur += datetime.timedelta(days=1)
    return count


def calculate_deemed_approval_date(
    fee_payment_date: datetime.date | str,
    holidays: set[str] | list[str],
    target_working_days: int = 46,
    clock_stopped_days: int = 0,
) -> datetime.date:
    """Calculate the exact date when deemed approval takes effect (on the 46th working day).

    Rule:
        Counting starts on the working day after fee payment.
        When running working days reach 46 (i.e. exceeding 45 working days),
        deemed approval is triggered on that 46th working day.
    """
    d_pay = parse_date(fee_payment_date)
    cur = d_pay + datetime.timedelta(days=1)

    # Advance if clock was stopped due to query
    if clock_stopped_days > 0:
        cur += datetime.timedelta(days=clock_stopped_days)

    working_days_counted = 0
    while working_days_counted < target_working_days:
        if is_working_day(cur, holidays):
            working_days_counted += 1
            if working_days_counted == target_working_days:
                return cur
        cur += datetime.timedelta(days=1)
    return cur


class ApplicationWorkflow:
    """Stateful workflow tracker for a single building-plan application."""

    def __init__(self, app_id: str, holidays: set[str] | list[str], has_scrutiny_violations: bool = False):
        self.app_id = app_id.strip()
        self.holidays = set(holidays)
        self.has_scrutiny_violations = has_scrutiny_violations

        self.submit_date: datetime.date | None = None
        self.fee_payment_date: datetime.date | None = None
        self.fee_amount: float = 0.0

        # Current state
        self.current_status: str = "SUBMITTED"
        self.current_stage: str | None = None
        self.current_stage_entry_date: datetime.date | None = None

        # Query tracking
        self.query_date: datetime.date | None = None
        self.query_response_date: datetime.date | None = None
        self.total_clock_stopped_days: int = 0

        # Lapse and Revival
        self.lapsed: bool = False
        self.lapse_date: datetime.date | None = None
        self.revival_count: int = 0
        self.revived_date: datetime.date | None = None

        # Approval & Commencement
        self.approval_date: datetime.date | None = None
        self.deemed_approval_date: datetime.date | None = None
        self.commencement_date: datetime.date | None = None
        self.suspended: bool = False
        self.suspension_date: datetime.date | None = None
        self.extension_count: int = 0

        # Recorded stage transitions for workflow.csv
        self.transitions: list[dict] = []

    def submit(self, submit_date: str | datetime.date) -> None:
        """Record initial submission."""
        self.submit_date = parse_date(submit_date)
        self.current_status = "SUBMITTED"

    def pay_fees(self, pay_date: str | datetime.date, amount: float, challan_ref: str = "") -> None:
        """Record fee payment. Timer starts and application enters SCRUTINY."""
        d = parse_date(pay_date)
        if self.fee_payment_date is None:
            self.fee_payment_date = d
            self.fee_amount = float(amount)
            # Enters SCRUTINY on payment date
            self.current_stage = "SCRUTINY"
            self.current_stage_entry_date = d
            self.current_status = "SCRUTINY"
        else:
            # Subsequent payment (e.g. revival fee or revalidation fee)
            pass

    def record_stage_result(self, stage: str, result_date: str | datetime.date, result: str) -> dict:
        """Record the official outcome of a statutory stage."""
        d_res = parse_date(result_date)
        stage_name = stage.strip().upper()
        res_name = result.strip().upper()

        if self.current_stage is None or self.fee_payment_date is None:
            raise RuntimeError(f"Cannot record stage result for {self.app_id}: fees not paid.")

        # Check if deemed approval occurred before this stage result
        self._check_deemed_approval_up_to(d_res)
        if self.current_status == "DEEMED_APPROVED":
            return self.transitions[-1]

        entry_date = self.current_stage_entry_date or self.fee_payment_date
        working_days = count_working_days(entry_date, d_res, self.holidays, inclusive_start=False, inclusive_end=True)

        if stage_name == "SCRUTINY":
            if res_name == "CLEARED":
                status_after = "SITE_INSPECTION"
                next_stage = "SITE_INSPECTION"
            else:
                status_after = "QUERY"
                next_stage = "QUERY"
        elif stage_name == "SITE_INSPECTION":
            if res_name == "CLEARED":
                status_after = "TECHNICAL"
                next_stage = "TECHNICAL"
            else:
                status_after = "QUERY"
                next_stage = "QUERY"
        elif stage_name == "TECHNICAL":
            if res_name == "APPROVED":
                status_after = "APPROVED"
                next_stage = None
                self.approval_date = d_res
            elif res_name == "QUERY":
                status_after = "QUERY"
                next_stage = "QUERY"
                self.query_date = d_res
            else:
                status_after = res_name
                next_stage = None
        else:
            status_after = res_name
            next_stage = None

        row = {
            "app_id": self.app_id,
            "stage": stage_name,
            "entered_date": entry_date.isoformat(),
            "exited_date": d_res.isoformat(),
            "working_days": working_days,
            "clock_stopped_days": 0,
            "status_after": status_after,
            "deemed_approval_date": format_date(self.deemed_approval_date),
        }
        self.transitions.append(row)

        self.current_status = status_after
        self.current_stage = next_stage
        self.current_stage_entry_date = d_res
        return row

    def respond_to_query(self, response_date: str | datetime.date) -> dict:
        """Record applicant's response to an outstanding query."""
        d_resp = parse_date(response_date)
        if self.query_date is None:
            raise RuntimeError(f"No active query to respond to for {self.app_id}.")

        # Calendar days between query and response
        calendar_days = (d_resp - self.query_date).days
        self.total_clock_stopped_days += calendar_days

        row = {
            "app_id": self.app_id,
            "stage": "TECHNICAL",
            "entered_date": self.query_date.isoformat(),
            "exited_date": d_resp.isoformat(),
            "working_days": 0,
            "clock_stopped_days": calendar_days,
            "status_after": "TECHNICAL",
            "deemed_approval_date": format_date(self.deemed_approval_date),
        }
        self.transitions.append(row)

        self.query_response_date = d_resp
        self.current_status = "TECHNICAL"
        self.current_stage = "TECHNICAL"
        self.current_stage_entry_date = d_resp
        self.query_date = None
        return row

    def lapse(self, lapse_date: str | datetime.date) -> None:
        """Mark application as lapsed due to 30-day query response timeout."""
        d = parse_date(lapse_date)
        self.lapsed = True
        self.lapse_date = d
        self.current_status = "LAPSED"

    def revive(self, request_date: str | datetime.date) -> bool:
        """Revive a lapsed application (allowed once within 60 days of lapse)."""
        d = parse_date(request_date)
        if not self.lapsed or self.lapse_date is None:
            return False
        if self.revival_count >= 1:
            return False  # Only one revival allowed

        days_since_lapse = (d - self.lapse_date).days
        if days_since_lapse > 60:
            return False  # Exceeded 60-day revival window

        self.revival_count += 1
        self.lapsed = False
        self.revived_date = d
        self.current_status = "REVIVED"
        return True

    def report_commencement(self, report_date: str | datetime.date) -> bool:
        """Record commencement of construction work."""
        d = parse_date(report_date)
        if self.approval_date is None and self.deemed_approval_date is None:
            return False

        appr_d = self.approval_date or self.deemed_approval_date
        assert appr_d is not None

        # Check 6-month commencement deadline
        # Approximate 6 calendar months: 182 days or month delta
        approx_six_months = appr_d + datetime.timedelta(days=182)
        if d > approx_six_months:
            self.suspended = True
            self.suspension_date = approx_six_months
            self.current_status = "SUSPENDED"

        self.commencement_date = d
        return True

    def pay_revalidation_fee(self, pay_date: str | datetime.date, amount: float) -> bool:
        """Pay Rs 5,000 fee to lift suspension and revalidate approval."""
        if self.suspended:
            self.suspended = False
            self.current_status = "APPROVED"
            return True
        return False

    def request_extension(self, request_date: str | datetime.date) -> bool:
        """Request 1-year extension. First is granted at 10% fee; second is rejected."""
        if self.extension_count == 0:
            self.extension_count += 1
            return True  # Granted
        return False  # Second extension rejected

    def _check_deemed_approval_up_to(self, as_of_date: datetime.date) -> None:
        """Evaluate if deemed approval took effect prior to as_of_date."""
        if self.fee_payment_date is None:
            return
        if self.current_status in ("APPROVED", "DEEMED_APPROVED"):
            return
        if self.has_scrutiny_violations:
            return  # Ineligible for deemed approval if scrutiny violations exist

        deemed_date = calculate_deemed_approval_date(
            self.fee_payment_date,
            self.holidays,
            target_working_days=46,
            clock_stopped_days=self.total_clock_stopped_days,
        )

        if deemed_date <= as_of_date:
            self.deemed_approval_date = deemed_date
            self.current_status = "DEEMED_APPROVED"

            entry_d = self.current_stage_entry_date or self.fee_payment_date
            stage_name = self.current_stage or "TECHNICAL"
            wd = count_working_days(entry_d, deemed_date, self.holidays, inclusive_start=False, inclusive_end=True)

            row = {
                "app_id": self.app_id,
                "stage": stage_name,
                "entered_date": entry_d.isoformat(),
                "exited_date": deemed_date.isoformat(),
                "working_days": wd,
                "clock_stopped_days": 0,
                "status_after": "DEEMED_APPROVED",
                "deemed_approval_date": deemed_date.isoformat(),
            }
            self.transitions.append(row)
            self.current_stage = None
            self.current_stage_entry_date = deemed_date

    def evaluate_as_of(self, as_of_date: str | datetime.date) -> str:
        """Evaluate and return final status as of a specified calendar date."""
        d = parse_date(as_of_date)
        self._check_deemed_approval_up_to(d)
        return self.current_status


def execute_workflow_commands(
    commands: list[str],
    holidays: set[str] | list[str],
    applications: list[dict] | None = None,
) -> dict[str, ApplicationWorkflow]:
    """Process workflow commands strictly in source file order."""
    holidays_set = set(holidays)
    workflows: dict[str, ApplicationWorkflow] = {}

    for line in commands:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue

        parts = line_clean.split("|")
        cmd = parts[0].strip()
        app_id = parts[1].strip() if len(parts) > 1 else ""

        if app_id and app_id not in workflows:
            workflows[app_id] = ApplicationWorkflow(app_id, holidays_set)

        wf = workflows.get(app_id)
        if wf is None:
            continue

        if cmd == "SUBMIT":
            submit_date = parts[2].strip()
            wf.submit(submit_date)

        elif cmd == "FEE_PAYMENT":
            pay_date = parts[2].strip()
            amount = float(parts[3].strip())
            challan = parts[4].strip() if len(parts) > 4 else ""
            wf.pay_fees(pay_date, amount, challan)

        elif cmd == "STAGE_RESULT":
            stage = parts[2].strip()
            res_date = parts[3].strip()
            result = parts[4].strip()
            wf.record_stage_result(stage, res_date, result)

        elif cmd == "QUERY_RESPONSE":
            resp_date = parts[2].strip()
            wf.respond_to_query(resp_date)

        elif cmd == "REVIVE":
            req_date = parts[2].strip()
            wf.lapse(parts[2].strip())  # ensure lapsed status before revive
            wf.revive(req_date)

        elif cmd == "COMMENCEMENT":
            comm_date = parts[2].strip()
            wf.report_commencement(comm_date)

        elif cmd == "REVALIDATION_FEE":
            pay_date = parts[2].strip()
            amt = float(parts[3].strip())
            wf.pay_revalidation_fee(pay_date, amt)

        elif cmd == "EXTENSION":
            req_date = parts[2].strip()
            wf.request_extension(req_date)

        elif cmd == "PRINT_WORKFLOW":
            as_of_date = parts[2].strip() if len(parts) > 2 else "2026-10-31"
            wf.evaluate_as_of(as_of_date)

    return workflows

