# Municipal Building-Plan Approval Fee and FAR Compliance Engine

- **Capstone Project:** Team T060
- **Problem Statement:** PS-115
- **Team Members:** Bheemesh V (1AT24CG016), Blessen Thomas (1AT24CG017)
- **Repository:** [https://github.com/blessen-thomas/T060-PS-115](https://github.com/blessen-thomas/T060-PS-115)

---

## 1. Project Overview

The **T060-PS-115 Compliance Engine** is a robust, file-driven municipal automation system designed for Urban Local Bodies (ULBs) and town planning authorities. It validates architectural building-plan sanction proposals against statutory municipal regulations, calculates itemized fee demands, manages the statutory approval lifecycle, and evaluates as-built completion certificate (CC) deviations.

### Main Features
- **Plan Validation**: Multi-rule compliance verification in strict statutory precedence order (`ZONING_USE` $\rightarrow$ `FAR` $\rightarrow$ `GROUND_COVERAGE` $\rightarrow$ `SETBACKS` $\rightarrow$ `HEIGHT_LIMIT` $\rightarrow$ `PARKING`).
- **Fee Demand Estimation**: Exact computation of scrutiny fees (with a ₹2,000 statutory minimum), development charges, premium FAR fees, agricultural betterment levies, labour welfare cess, and parking shortfall penalties, with component-wise ceiling rounding up to the nearest ₹10.
- **Statutory Workflow Management**: Full lifecycle tracking across `SCRUTINY` (7 days), `SITE_INSPECTION` (10 days), and `TECHNICAL` (15 days), featuring working-day calendar math (excluding weekends and gazetted public holidays), query clock pauses, lapse and revival tracking, and automatic 46th working day deemed approvals.
- **Completion Certificate (CC) Assessment**: As-built deviation evaluation supporting area compounding (2× development charge for $\le 5\%$, 4× for $5\text{--}10\%$, refusal $> 10\%$), setback compounding (₹10,000 per metre-side for $\le 0.30\text{ m}$), and strict refusal for any positive height overage ($> 0.0\text{ m}$).
- **Batch Command Pipeline**: Sequential, deterministic execution of all 292 lifecycle commands from `commands.txt` exporting four standardized output CSV reports directly into `outputs/`.

---

## 2. Technology Stack

- **Language**: Python 3.10+ (Standard Library: `csv`, `datetime`, `math`, `argparse`, `pathlib`)
- **Testing Framework**: `pytest` (v8.0.0+)
- **Operating Environment**: Windows PowerShell / POSIX Shell

---

## 3. Project Structure

```text
T060-PS-115/
│
├── data/                                       # Official municipal data pack
│   ├── applications.csv                        # 40 building-plan applications
│   ├── commands.txt                            # 292 sequential municipal lifecycle commands
│   ├── coverage_table.csv                      # Maximum ground coverage by plot-area band
│   ├── far_table.csv                           # Permitted base FAR by road width & building use
│   ├── fee_schedule.csv                        # Statutory municipal fee schedule & rates
│   ├── floors.csv                              # Floor-level built-up and balcony areas (178 rows)
│   ├── holidays.csv                            # 2026 public holiday calendar for working-day clock
│   ├── setback_table.csv                       # Setback requirements by road width & plot width
│   ├── zones.csv                               # Municipal zones, permitted uses, & height caps
│   └── README.md                               # Data pack specification and scenarios
│
├── docs/                                       # Project documentation
│   ├── T060_PS115_Software_Design_Document.pdf # Formal Software Design Document (SDD)
│   ├── decision_log.md                         # Technical and architectural decision log
│   └── demo_video.md                           # Demonstration video link and contents outline
│
├── outputs/                                    # Generated official municipal reports
│   ├── validation_report.csv                   # Plan validation compliance report (40 rows)
│   ├── fee_demand.csv                          # Itemized fee demand breakdown report (30 rows)
│   ├── workflow.csv                            # Lifecycle stage transition audit log (76 rows)
│   └── cc_decisions.csv                        # Completion certificate decision report (6 rows)
│
├── src/                                        # Modular application source code
│   ├── __init__.py                             # Package marker
│   ├── data_loader.py                          # CSV loading and strict interval lookup utilities
│   ├── far.py                                  # Core FAR calculation, deductions, and caps
│   ├── rules.py                                # Zoning, coverage, setbacks, height, & parking rules
│   ├── fees.py                                 # Municipal fee engine and demand calculation
│   ├── workflow.py                             # Calendar math, stage tracker, and deemed approval
│   ├── cc.py                                   # Completion certificate & deviation compounding
│   ├── runner.py                               # End-to-end command runner & CSV exporter
│   └── cli.py                                  # Interactive CLI for single-plan verification
│
├── tests/                                      # Automated test suite (171 tests)
│   ├── test_data_loader.py                     # CSV parsing and interval boundary tests (17 tests)
│   ├── test_far.py                             # FAR calculations, caps, and road bands (48 tests)
│   ├── test_rules.py                           # Regulatory validation rules & edge cases (52 tests)
│   ├── test_fees.py                            # Fee components & payment verification (27 tests)
│   ├── test_workflow.py                        # Calendar math, query stops, & deemed approvals (12 tests)
│   ├── test_cc.py                              # As-built deviation slabs & compounding (11 tests)
│   └── test_runner.py                          # Full pipeline execution & determinism (4 tests)
│
├── .gitignore                                  # Git exclusion configuration
├── README.md                                   # Project documentation & run guide
└── requirements.txt                            # Test suite dependencies (pytest)
```

---

## 4. Prerequisites

Before setting up the project, ensure you have:
- **Python**: Version 3.10 or higher installed (`python --version`).
- **pip**: Python package installer (`pip --version`).
- **Git**: Version control tool (`git --version`).
- **Shell**: Windows PowerShell (or standard Bash on Linux/macOS).

---

## 5. Installation and Setup

Follow these copy-paste-ready commands in Windows PowerShell:

```powershell
# 1. Clone the repository
git clone https://github.com/blessen-thomas/T060-PS-115.git

# 2. Navigate into the project root directory
cd T060-PS-115

# 3. Create a Python virtual environment (.venv)
python -m venv .venv

# 4. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 5. Install dependencies from requirements.txt
pip install -r requirements.txt
```

---

## 6. Running the Application

### End-to-End Command Pipeline
To process all 292 lifecycle commands from `data/commands.txt` and generate all four municipal CSV reports inside `outputs/`:

```powershell
python -m src.runner data/commands.txt --data-dir data --output-dir outputs
```

*(Note: The command runner defaults to `--output-dir outputs`, so running `python -m src.runner data/commands.txt --data-dir data` produces the same result.)*

**What this command does:**
1. Loads all municipal regulations, holiday calendars, 40 applications, and 178 floor records from `--data-dir data`.
2. Validates every application in statutory precedence order and determines compliance.
3. Generates itemized fee demands for compliant applications (excluding non-compoundable plans).
4. Processes all 292 sequential commands strictly in file order, tracking workflow stages, working days, calendar query halts, lapses, revivals, deemed approvals, commencement notices, extensions, and completion certificates.
5. Exports the four official output CSV files directly into `--output-dir outputs`.

### Interactive Single-Plan CLI
For interactive plan checking and manual FAR/fee calculations:

```powershell
python src/cli.py
```

---

## 7. Running Tests

To execute the complete automated test suite of 171 tests with verbose reporting:

```powershell
python -m pytest -v
```

All 171 test cases run in approximately 0.25 seconds with 100% pass rate, verifying:
- CSV loading, interval parsing, and data integrity (17 tests).
- FAR base calculations, exclusions, premium bounds, and road width bands (48 tests).
- Zoning, ground coverage, setback boundaries, corner plots, height limits, parking deficits, and modular FAR rules (52 tests).
- Fee formulas, minimum scrutiny fees, rounding rules, and 27 official payment receipts (27 tests).
- Working days, holiday skipping, 30-day query stops, 60-day revivals, and 46th-day deemed approvals (12 tests).
- Completion certificate deviation slabs, setback compounding, and height refusals (11 tests).
- End-to-end command runner order, CSV schemas, and pipeline determinism (4 tests).

---

## 8. Output Files

The pipeline generates four deliverable CSV files inside the `outputs/` directory:

| Output File | Rows | Description & Key Invariants |
|---|:---:|---|
| **`outputs/validation_report.csv`** | **40** | One row per application; lists violations in statutory precedence order (`ZONING_USE` $\rightarrow$ `FAR` $\rightarrow$ `GROUND_COVERAGE` $\rightarrow$ `SETBACKS` $\rightarrow$ `HEIGHT_LIMIT` $\rightarrow$ `PARKING`); compliant applications emit a `NONE` row. |
| **`outputs/fee_demand.csv`** | **30** | Itemized fee breakdown for applications with no non-compoundable violations; strictly excludes the 10 unapprovable applications. |
| **`outputs/workflow.csv`** | **76** | Chronological log of all stage transitions (`SCRUTINY`, `SITE_INSPECTION`, `TECHNICAL`), working days elapsed, query clock pauses, lapses, revivals, and deemed approvals. |
| **`outputs/cc_decisions.csv`** | **6** | Completion certificate decisions for all 6 `CC_REQUEST` records (4 `CC_ISSUED`, 2 `CC_REFUSED`). |

---

## 9. Documentation

Working relative links to official submission documentation:
- **Software Design Document (SDD)**: [`docs/T060_PS115_Software_Design_Document.pdf`](docs/T060_PS115_Software_Design_Document.pdf) — Complete architectural overview, UML class and state diagrams, domain glossary, and business-rule register.
- **Engineering Decision Log**: [`docs/decision_log.md`](docs/decision_log.md) — Technical and architectural decisions (D-01 through D-18) explaining technology choices, data handling, and regulatory logic.
- **Demonstration Video Outline**: [`docs/demo_video.md`](docs/demo_video.md) — Outline and link placeholder for the five-minute project demonstration video.

---

## 10. Limitations

- **Headless Execution**: The system is designed as a headless, file-driven command-line engine and batch pipeline. It does not provide a web user interface (GUI) or browser frontend.
- **Statutory Scope**: Enforces the specific municipal planning rules, setback tables, height caps, and fee structures defined in the PS-115 problem statement.
- **Data Persistence**: Operates directly on structured CSV and command stream text files; does not require an external SQL or NoSQL database server.
