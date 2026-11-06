"""Unit and integration tests for the Municipal Workflow Engine (PS-115).

Covers:
- Working day and holiday rules (excluding weekends and official municipal holidays)
- Next working day logic
- 46th working day calculation for deemed approval
- Official planted scenario EC-07: APP-0001 deemed approval on 2026-03-18
- Official planted scenario EC-06: APP-0019 query response on day 30 (clock resumption)
- Official planted scenario: APP-0023 query timeout -> lapse -> one-time revival -> approval
- Official planted scenario: APP-0034 clean application with unpaid fees (timer never starts)
- Official planted scenario: APP-0008 commencement not within 6 months -> suspended -> revalidated
- Official planted scenario: APP-0011 1st extension granted, 2nd extension rejected
- Full execution of all 292 commands from commands.txt
"""

from __future__ import annotations

import datetime
import pathlib
import pytest

from src.data_loader import load_data_pack, load_holidays
from src.workflow import (
    ApplicationWorkflow,
    calculate_deemed_approval_date,
    count_working_days,
    execute_workflow_commands,
    get_next_working_day,
    is_working_day,
    parse_date,
)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def holidays():
    """Load the official 2026 holiday set."""
    return load_holidays(DATA_DIR / "holidays.csv")


# ==============================================================================
# 1. Working Day and Calendar Logic Tests
# ==============================================================================

def test_is_working_day_weekdays_and_weekends(holidays):
    """Mon-Fri are working days unless they are official holidays; Sat/Sun never are."""
    # 2026-01-07 is Wednesday (normal working day)
    assert is_working_day("2026-01-07", holidays) is True
    # 2026-01-10 is Saturday
    assert is_working_day("2026-01-10", holidays) is False
    # 2026-01-11 is Sunday
    assert is_working_day("2026-01-11", holidays) is False


def test_is_working_day_excludes_official_holidays(holidays):
    """Official holidays from holidays.csv are excluded even if on a weekday."""
    # 2026-01-15 is Thursday (Makara Sankranti)
    assert is_working_day("2026-01-15", holidays) is False
    # 2026-01-26 is Monday (Republic Day)
    assert is_working_day("2026-01-26", holidays) is False
    # 2026-05-01 is Friday (May Day)
    assert is_working_day("2026-05-01", holidays) is False


def test_get_next_working_day(holidays):
    """Returns the immediately following working day, skipping weekends and holidays."""
    # Friday 2026-01-09 -> next working day is Monday 2026-01-12
    assert get_next_working_day("2026-01-09", holidays) == datetime.date(2026, 1, 12)
    # Wednesday 2026-01-14 -> Thursday 2026-01-15 is a holiday -> Friday 2026-01-16
    assert get_next_working_day("2026-01-14", holidays) == datetime.date(2026, 1, 16)


def test_count_working_days(holidays):
    """Accurately count working days across weekends and official holidays."""
    # Jan 12 (Mon) to Jan 14 (Wed) = 3 working days (Jan 12, 13, 14)
    cnt = count_working_days("2026-01-12", "2026-01-14", holidays, inclusive_start=True, inclusive_end=True)
    assert cnt == 3

    # Jan 14 (Wed) to Jan 16 (Fri), exclusive of Jan 14:
    # Jan 15 is holiday (Makara Sankranti), Jan 16 is working day -> 1 working day
    cnt_holiday = count_working_days("2026-01-14", "2026-01-16", holidays, inclusive_start=False, inclusive_end=True)
    assert cnt_holiday == 1


# ==============================================================================
# 2. Deemed Approval Tests (APP-0001 Planted Case)
# ==============================================================================

def test_app_0001_deemed_approval_exact_date(holidays):
    """Official EC-07: APP-0001 fee paid 2026-01-09, deemed approved on 46th working day (2026-03-18)."""
    fee_payment_date = "2026-01-09"
    deemed_date = calculate_deemed_approval_date(fee_payment_date, holidays, target_working_days=46)
    assert deemed_date == datetime.date(2026, 3, 18)


def test_app_0001_workflow_execution(holidays):
    """Trace APP-0001 through stages to deemed approval."""
    wf = ApplicationWorkflow("APP-0001", holidays)
    wf.submit("2026-01-07")
    wf.pay_fees("2026-01-09", 340990.00, "CHL433179143")
    assert wf.current_status == "SCRUTINY"

    # Scrutiny cleared on 2026-01-14
    wf.record_stage_result("SCRUTINY", "2026-01-14", "CLEARED")
    assert wf.current_status == "SITE_INSPECTION"

    # Site inspection cleared on 2026-02-13
    wf.record_stage_result("SITE_INSPECTION", "2026-02-13", "CLEARED")
    assert wf.current_status == "TECHNICAL"

    # TECHNICAL never decides; evaluate as of 2026-10-31
    final_status = wf.evaluate_as_of("2026-10-31")
    assert final_status == "DEEMED_APPROVED"
    assert wf.deemed_approval_date == datetime.date(2026, 3, 18)

    # Check transitions recorded
    transitions = wf.transitions
    assert len(transitions) == 3
    assert transitions[0]["stage"] == "SCRUTINY"
    assert transitions[1]["stage"] == "SITE_INSPECTION"
    assert transitions[2]["stage"] == "TECHNICAL"
    assert transitions[2]["status_after"] == "DEEMED_APPROVED"
    assert transitions[2]["exited_date"] == "2026-03-18"


# ==============================================================================
# 3. Query Clock Stoppage Tests (APP-0019 Planted Case)
# ==============================================================================

def test_app_0019_query_response_on_day_30(holidays):
    """Official EC-06: APP-0019 responds on the 30th calendar day; clock pauses then resumes."""
    wf = ApplicationWorkflow("APP-0019", holidays)
    wf.submit("2026-03-23")
    wf.pay_fees("2026-03-27", 428750.00, "CHL713274404")
    wf.record_stage_result("SCRUTINY", "2026-04-02", "CLEARED")
    wf.record_stage_result("SITE_INSPECTION", "2026-04-10", "CLEARED")

    # Technical issues QUERY on 2026-04-23
    wf.record_stage_result("TECHNICAL", "2026-04-23", "QUERY")
    assert wf.current_status == "QUERY"

    # Applicant responds on 2026-05-23 (exactly 30 days)
    row = wf.respond_to_query("2026-05-23")
    assert row["clock_stopped_days"] == 30
    assert wf.current_status == "TECHNICAL"

    # Technical approves on 2026-06-02
    wf.record_stage_result("TECHNICAL", "2026-06-02", "APPROVED")
    assert wf.current_status == "APPROVED"
    assert wf.approval_date == datetime.date(2026, 6, 2)


# ==============================================================================
# 4. Lapse and Revival Tests (APP-0023 Planted Case)
# ==============================================================================

def test_app_0023_query_timeout_lapse_and_revival(holidays):
    """Official scenario: APP-0023 lapses after 30 days, revives within 60 days with 25% fee."""
    wf = ApplicationWorkflow("APP-0023", holidays)
    wf.submit("2026-04-06")
    wf.pay_fees("2026-04-09", 277430.00, "CHL744158662")
    wf.record_stage_result("SCRUTINY", "2026-04-20", "CLEARED")
    wf.record_stage_result("SITE_INSPECTION", "2026-04-27", "CLEARED")
    wf.record_stage_result("TECHNICAL", "2026-05-05", "QUERY")

    # Lapse after 30 days (query on May 5 -> lapse on June 4 / June 5)
    wf.lapse("2026-06-05")
    assert wf.current_status == "LAPSED"

    # Revived on 2026-06-30 (25 days after lapse, well within 60-day limit)
    revived = wf.revive("2026-06-30")
    assert revived is True
    assert wf.current_status == "REVIVED"

    # Second revival attempt must be rejected
    wf.lapse("2026-08-01")
    second_revival = wf.revive("2026-08-10")
    assert second_revival is False


# ==============================================================================
# 5. Unpaid Fee Gate (APP-0034 Planted Case)
# ==============================================================================

def test_app_0034_unpaid_fees_timer_never_starts(holidays):
    """Official scenario: APP-0034 fees are never paid; timer never starts; no deemed approval."""
    wf = ApplicationWorkflow("APP-0034", holidays)
    wf.submit("2026-06-03")

    # No fee payment made
    status_as_of = wf.evaluate_as_of("2026-10-31")
    assert status_as_of == "SUBMITTED"
    assert wf.fee_payment_date is None
    assert wf.deemed_approval_date is None
    assert len(wf.transitions) == 0


# ==============================================================================
# 6. Commencement and Suspension Tests (APP-0008 Planted Case)
# ==============================================================================

def test_app_0008_commencement_suspension_and_revalidation(holidays):
    """Official scenario: APP-0008 approved Feb 25, suspended after 6 months, revalidated for Rs 5,000."""
    wf = ApplicationWorkflow("APP-0008", holidays)
    wf.submit("2026-01-19")
    wf.pay_fees("2026-01-23", 5573760.00, "CHL179785575")
    wf.record_stage_result("SCRUTINY", "2026-02-03", "CLEARED")
    wf.record_stage_result("SITE_INSPECTION", "2026-02-13", "CLEARED")
    wf.record_stage_result("TECHNICAL", "2026-02-25", "APPROVED")
    assert wf.current_status == "APPROVED"

    # More than 6 months without commencement (Feb 25 -> Aug 25+)
    # Attempting commencement on 2026-09-08 without prior notice detects suspension
    wf.report_commencement("2026-09-08")
    assert wf.suspended is True
    assert wf.current_status == "SUSPENDED"

    # Revalidation fee paid on 2026-09-06
    revalidated = wf.pay_revalidation_fee("2026-09-06", 5000.00)
    assert revalidated is True
    assert wf.current_status == "APPROVED"


# ==============================================================================
# 7. Extension Tests (APP-0011 Planted Case)
# ==============================================================================

def test_app_0011_extension_rules(holidays):
    """Official scenario: APP-0011 first extension granted; second extension rejected."""
    wf = ApplicationWorkflow("APP-0011", holidays)
    wf.submit("2026-01-27")
    wf.pay_fees("2026-01-28", 11219950.00, "CHL191722903")
    wf.record_stage_result("SCRUTINY", "2026-02-04", "CLEARED")
    wf.record_stage_result("SITE_INSPECTION", "2026-02-16", "CLEARED")
    wf.record_stage_result("TECHNICAL", "2026-03-02", "APPROVED")

    # First extension request: granted
    ext1 = wf.request_extension("2026-07-30")
    assert ext1 is True

    # Second extension request: rejected
    ext2 = wf.request_extension("2026-09-08")
    assert ext2 is False


# ==============================================================================
# 8. Full End-to-End Command Processing (All 292 Commands)
# ==============================================================================

def test_execute_workflow_commands_full_dataset(holidays):
    """Execute all 292 commands from commands.txt and verify expected statuses."""
    commands_file = DATA_DIR / "commands.txt"
    commands = commands_file.read_text().splitlines()

    workflows = execute_workflow_commands(commands, holidays)

    # Total 40 applications processed
    assert len(workflows) == 40

    # Verify key applications
    assert workflows["APP-0001"].evaluate_as_of("2026-10-31") == "DEEMED_APPROVED"
    assert workflows["APP-0001"].deemed_approval_date == datetime.date(2026, 3, 18)

    assert workflows["APP-0002"].evaluate_as_of("2026-10-31") == "APPROVED"
    assert workflows["APP-0019"].evaluate_as_of("2026-10-31") == "APPROVED"
    assert workflows["APP-0023"].evaluate_as_of("2026-10-31") == "APPROVED"
    assert workflows["APP-0034"].evaluate_as_of("2026-10-31") == "SUBMITTED"
    assert workflows["APP-0034"].fee_payment_date is None
