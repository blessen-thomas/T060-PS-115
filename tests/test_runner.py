"""Unit and integration tests for the End-to-End Command Runner & 4-CSV Pipeline (PS-115).

Covers:
- Statutory rule validation precedence in validation_report.csv
- Correct generation of NONE rows for compliant plans
- Gating of fee_demand.csv (only plans without non-compoundable violations)
- Execution of all 292 commands from commands.txt strictly in file order
- Generation and schema verification of all 4 output CSV files:
  1. validation_report.csv (40 rows)
  2. fee_demand.csv (30 rows)
  3. workflow.csv (76 rows)
  4. cc_decisions.csv (6 rows)
- Deterministic output verification across repeated runs
"""

from __future__ import annotations

import csv
import pathlib
import pytest

from src.data_loader import load_data_pack
from src.runner import (
    RULE_PRECEDENCE,
    generate_validation_report,
    run_command_pipeline,
    validate_application,
)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def data_pack():
    """Load the full official dataset once."""
    return load_data_pack(DATA_DIR)


# ==============================================================================
# 1. Validation Report Tests
# ==============================================================================

def test_generate_validation_report_row_count_and_none_rows(data_pack):
    """Verify exactly 40 rows: 12 violation rows + 28 NONE rows."""
    report = generate_validation_report(
        applications=data_pack["applications"],
        floors_by_app=data_pack["floors_by_app"],
        data_pack=data_pack,
    )

    assert len(report) == 40

    none_rows = [r for r in report if r["rule_id"] == "NONE"]
    violation_rows = [r for r in report if r["rule_id"] != "NONE"]

    assert len(none_rows) == 28
    assert len(violation_rows) == 12

    # Check exact columns
    expected_cols = ["app_id", "rule_id", "check", "required", "proposed", "compoundable"]
    for r in report:
        assert list(r.keys()) == expected_cols


def test_validation_report_sorting_and_precedence(data_pack):
    """Verify that reports are ordered by app_id and follow rule precedence."""
    report = generate_validation_report(
        applications=data_pack["applications"],
        floors_by_app=data_pack["floors_by_app"],
        data_pack=data_pack,
    )

    app_ids = [r["app_id"] for r in report]
    assert app_ids == sorted(app_ids)

    # For any app with multiple violations, precedence order must be respected
    # Check that rule_id order adheres to RULE_PRECEDENCE
    prev_app = ""
    prev_prec = -1
    for r in report:
        aid = r["app_id"]
        rid = r["rule_id"]
        if rid == "NONE":
            continue
        prec = RULE_PRECEDENCE.index(rid) if rid in RULE_PRECEDENCE else 999
        if aid == prev_app:
            assert prec >= prev_prec
        prev_app = aid
        prev_prec = prec


# ==============================================================================
# 2. Pipeline Execution & 4-CSV File Generation
# ==============================================================================

def test_run_command_pipeline_end_to_end(tmp_path, data_pack):
    """Execute all 292 commands and verify all 4 generated CSV files in a temp directory."""
    commands_path = DATA_DIR / "commands.txt"

    results = run_command_pipeline(
        commands_path=commands_path,
        data_dir=DATA_DIR,
        output_dir=tmp_path,
        print_output=False,
    )

    # 1. Validation Report verification
    val_file = tmp_path / "validation_report.csv"
    assert val_file.exists()
    with val_file.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 40
        assert reader[0]["app_id"] == "APP-0001"
        assert reader[0]["rule_id"] == "NONE"

    # 2. Fee Demand verification
    fee_file = tmp_path / "fee_demand.csv"
    assert fee_file.exists()
    with fee_file.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 30
        fee_apps = [r["app_id"] for r in reader]
        # Verify clean apps are present
        assert "APP-0001" in fee_apps
        assert "APP-0002" in fee_apps
        # Verify fatal violation apps are excluded
        assert "APP-0003" not in fee_apps
        assert "APP-0014" not in fee_apps
        assert "APP-0015" not in fee_apps
        assert "APP-0032" not in fee_apps

    # 3. Workflow verification
    wf_file = tmp_path / "workflow.csv"
    assert wf_file.exists()
    with wf_file.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 76
        # Check APP-0001 deemed approval
        app_0001_rows = [r for r in reader if r["app_id"] == "APP-0001"]
        assert len(app_0001_rows) == 3
        assert app_0001_rows[-1]["status_after"] == "DEEMED_APPROVED"
        assert app_0001_rows[-1]["deemed_approval_date"] == "2026-03-18"

    # 4. CC Decisions verification
    cc_file = tmp_path / "cc_decisions.csv"
    assert cc_file.exists()
    with cc_file.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 6
        cc_map = {r["app_id"]: r["decision"] for r in reader}
        assert cc_map["APP-0013"] == "CC_REFUSED"
        assert cc_map["APP-0010"] == "CC_ISSUED"
        assert cc_map["APP-0009"] == "CC_ISSUED"
        assert cc_map["APP-0002"] == "CC_ISSUED"
        assert cc_map["APP-0006"] == "CC_REFUSED"
        assert cc_map["APP-0007"] == "CC_ISSUED"


# ==============================================================================
# 3. Determinism Test Across Consecutive Runs
# ==============================================================================

def test_pipeline_determinism(tmp_path):
    """Ensure two consecutive pipeline executions produce bitwise-identical CSV files."""
    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"

    commands_path = DATA_DIR / "commands.txt"

    run_command_pipeline(commands_path, DATA_DIR, output_dir=run1_dir)
    run_command_pipeline(commands_path, DATA_DIR, output_dir=run2_dir)

    for csv_name in ["validation_report.csv", "fee_demand.csv", "workflow.csv", "cc_decisions.csv"]:
        f1_content = (run1_dir / csv_name).read_bytes()
        f2_content = (run2_dir / csv_name).read_bytes()
        assert f1_content == f2_content, f"Output mismatch between consecutive runs for {csv_name}"
