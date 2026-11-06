# Municipal Building-Plan Approval Fee and FAR Compliance Engine

**Capstone Project**: Team T060
**Problem Statement**: PS-115
**Team Members**: Bheemesh V (1AT24CG016), Blessen Thomas (1AT24CG017)
**Repository**: [https://github.com/blessen-thomas/T060-PS-115](https://github.com/blessen-thomas/T060-PS-115)
**Technology**: Python 3.10+, `pytest`, Standard Library, Command-Line Interface (CLI)

---

## 1. Project Overview

The **T060-PS-115 Compliance Engine** is a comprehensive, production-grade municipal automation system that processes building-plan sanction applications according to statutory town planning regulations.

The engine automates the full municipal plan lifecycle:
1. **Plan Validation**: Multi-rule compliance verification in statutory precedence order (Zoning $\rightarrow$ FAR $\rightarrow$ Coverage $\rightarrow$ Setbacks $\rightarrow$ Height $\rightarrow$ Parking).
2. **Fee Demand Estimation**: Calculation of scrutiny fees, development charges, premium FAR fees, betterment levies, labour cess, and parking shortfall penalties.
3. **Statutory Workflow Management**: Stage progression tracking (`SCRUTINY` $\rightarrow$ `SITE_INSPECTION` $\rightarrow$ `TECHNICAL`), working-day calendars, holiday exclusions, query clock stops, lapses, revivals, and 46th-day deemed approvals.
4. **Completion Certificate (CC) Assessment**: As-built deviation evaluation, compounding fee calculation for excess area ($\le 10\%$) and setbacks ($\le 0.30\text{ m}$), and strict refusal for height overages.
5. **Command Pipeline Execution**: Sequential execution of all 292 commands from `commands.txt` and deterministic generation of the 4 mandatory output CSV files.

---

## 2. Architecture & Codebase Layout

```text
T060-PS-115/
├── data/                       # Official municipal data pack
│   ├── applications.csv        # 40 building-plan applications
│   ├── commands.txt            # 292 sequential municipal lifecycle commands
│   ├── coverage_table.csv      # Maximum ground coverage by plot-area band
│   ├── far_table.csv           # Permitted base FAR by road width & building use
│   ├── fee_schedule.csv        # Statutory municipal fee schedule & rates
│   ├── floors.csv              # Floor-level built-up and balcony areas (178 rows)
│   ├── holidays.csv            # 2026 public holiday calendar for working-day clock
│   ├── setback_table.csv       # Setback requirements by road width & plot width
│   └── zones.csv               # Municipal zones, permitted uses, & height caps
├── docs/                       # Comprehensive documentation & viva guides
│   ├── design_document.md      # Full design document, diagrams, glossary, viva Q&A
│   └── dev_log.md              # Milestone-by-milestone development & decision log
├── src/                        # Modular application source code
│   ├── __init__.py             # Package marker
│   ├── data_loader.py          # CSV loading and strict interval lookup logic
│   ├── far.py                  # Core FAR calculation, deductions, and caps
│   ├── rules.py                # Zoning, coverage, setbacks, height, & parking rules
│   ├── fees.py                 # Municipal fee engine and demand calculation
│   ├── workflow.py             # Calendar math, stage tracker, and deemed approval
│   ├── cc.py                   # Completion certificate & deviation compounding
│   ├── runner.py               # End-to-end command runner & 4-CSV exporter
│   └── cli.py                  # Interactive CLI for plan checking
├── tests/                      # Automated test suite (162 tests)
│   ├── test_data_loader.py     # CSV parsing and interval boundary tests (17 tests)
│   ├── test_far.py             # FAR calculations, caps, and road bands (48 tests)
│   ├── test_rules.py           # Individual validation rules & edge cases (43 tests)
│   ├── test_fees.py            # Fee components & 27-payment verification (27 tests)
│   ├── test_workflow.py        # Calendar math, query stops, & deemed approvals (12 tests)
│   ├── test_cc.py              # As-built deviation slabs & compounding (11 tests)
│   └── test_runner.py          # Full pipeline execution & determinism (4 tests)
├── PS-115_PROJECT_CONTEXT.md   # Persistent project instructions & rules
├── requirements.txt            # Testing dependencies (pytest)
└── README.md                   # Project documentation & run guide
```

---

## 3. Quickstart & Execution Guide

### Prerequisites
- Python 3.10 or higher installed.
- Virtual environment (recommended).

### Installation
```bash
git clone https://github.com/blessen-thomas/T060-PS-115.git
cd T060-PS-115
pip install -r requirements.txt
```

### Running the Full Test Suite
To run all 162 automated tests with verbose output:
```bash
python -m pytest -v
```

### Running the End-to-End Command Pipeline
To process all 292 commands from `data/commands.txt` and generate all 4 output CSV files in the project root:
```bash
python -m src.runner data/commands.txt --data-dir data --output-dir .
```

### Running the Interactive CLI
For manual single-application FAR and fee compliance verification:
```bash
python src/cli.py
```

---

## 4. Generated Output CSV Files

When executed, the pipeline exports the 4 mandatory municipal reports:

| Output File | Target Rows | Description & Key Invariants |
|---|:---:|---|
| **`validation_report.csv`** | **40** | One row per application; lists violations in statutory precedence order (`ZONING_USE` $\rightarrow$ `FAR` $\rightarrow$ `GROUND_COVERAGE` $\rightarrow$ `SETBACKS` $\rightarrow$ `HEIGHT_LIMIT` $\rightarrow$ `PARKING`); compliant applications emit a `NONE` row. |
| **`fee_demand.csv`** | **30** | Fee demand breakdown for applications with no non-compoundable violations; 10 fatal applications are strictly excluded. |
| **`workflow.csv`** | **76** | Chronological log of all stage transitions (`SCRUTINY`, `SITE_INSPECTION`, `TECHNICAL`), working days, query clock pauses, lapses, revivals, and deemed approvals. |
| **`cc_decisions.csv`** | **6** | Completion certificate decisions for all 6 `CC_REQUEST` records (4 `CC_ISSUED`, 2 `CC_REFUSED`). |

---

## 5. Verified Planted Scenarios

| Application | Statutory Rule & Scenario | Expected Outcome | Test Status |
|---|---|---|:---:|
| **APP-0001** | Fee paid Jan 09; skips Jan 15 & Jan 26 holidays; Technical never decides | `DEEMED_APPROVED` on 46th working day (2026-03-18) | Verified |
| **APP-0002** | Road width 12 m, base FAR 2.25, Premium FAR 0.25 | All checks pass; fee ₹50,85,380 match | Verified |
| **APP-0003** | Premium FAR 0.50 + TDR 0.40 = 0.90 (exceeds 0.60 cap by 0.30) | `FAR_CAP` violation; fee demand blocked | Verified |
| **APP-0005** | Plot area 200 sq.m; ground coverage 63% $\le 65\%$ permitted | All checks pass; fee ₹1,29,470 match | Verified |
| **APP-0006** | As-built built-up area deviation +12.00% (> 10% maximum limit) | `CC_REFUSED` (area excess non-compoundable) | Verified |
| **APP-0007** | As-built built-up area deviation +10.00% (on the 10% ceiling) | `CC_ISSUED` (4× dev charge slab = ₹65,280) | Verified |
| **APP-0008** | Approved Feb 25; no commencement within 6 months | `SUSPENDED` Aug 25; revalidated with ₹5,000 | Verified |
| **APP-0009** | As-built built-up area deviation +5.00% | `CC_ISSUED` (2× dev charge slab = ₹8,190) | Verified |
| **APP-0010** | Setback deviation 0.30 m on 2 sides | `CC_ISSUED` (setback compounded = ₹6,000) | Verified |
| **APP-0011** | First extension request granted; second extension requested | 1st `EXTENSION` granted; 2nd `REJECTED` | Verified |
| **APP-0013** | As-built height +0.40 m above approved height | `CC_REFUSED` (height is never compoundable) | Verified |
| **APP-0014** | Ground coverage exceeds 60% on 201–500 sq.m plot | `GROUND_COVERAGE` violation; fees blocked | Verified |
| **APP-0015** | Front setback 4.0 m on 15 m road (needs 4.5 m) | `SETBACK_FRONT` violation; fees blocked | Verified |
| **APP-0017** | Parking 10 cars required, 8 proposed (exactly 20% shortfall) | `PARKING` passes; ₹4,00,000 shortfall fee | Verified |
| **APP-0018** | Side setback 1.20 m on 10.5 m plot width (deviation 0.30 m) | Compoundable setback; fees generated | Verified |
| **APP-0019** | Query issued; applicant responds on 30th calendar day | Clock paused for 30 days; approved Jun 02 | Verified |
| **APP-0020** | Corner plot secondary road setback 2.20 m (deviation 0.30 m) | Compoundable setback; fees generated | Verified |
| **APP-0021** | Commercial, Premium 0.50 + TDR 0.10 used, but built FAR exceeds allowed | `FAR_ACHIEVED` violation; fees blocked | Verified |
| **APP-0023** | Query timeout > 30 days $\rightarrow$ `LAPSED`; revived within 60 days | Revived on Jun 30 with 25% scrutiny fee | Verified |
| **APP-0024** | Corner plot with two equal 9.0 m roads | Front 3.0 m, second road side 2.5 m (passes) | Verified |
| **APP-0026** | Premium FAR requested on 9 m road (< 12 m) | `FAR_PREMIUM` road width violation | Verified |
| **APP-0027** | Parking 12 cars required, 9 proposed (25% shortfall > 20%) | `PARKING` violation; fees blocked | Verified |
| **APP-0029** | Rear setback 1.50 m on 15 m plot width (needs 2.0 m) | `SETBACK_REAR` violation; fees blocked | Verified |
| **APP-0031** | Building height 16.0 m on 7.5 m road (exceeds 15 m zone cap) | `HEIGHT_LIMIT` violation; fees blocked | Verified |
| **APP-0032** | Commercial use in residential-only zone ZN-R1 | `ZONING_USE` violation (first precedence) | Verified |
| **APP-0034** | Clean application where fees are never paid | Timer never starts; no deemed approval | Verified |
| **APP-0035** | FAR above base on 10 m road (no premium allowed) | `FAR_ACHIEVED` violation; fees blocked | Verified |

---

## 6. Documentation & Viva Readiness

Detailed engineering design documentation, Mermaid UML class and state diagrams, a complete decision log, and oral examination defense Q&A are available in:
- [`docs/design_document.md`](docs/design_document.md)
- [`docs/dev_log.md`](docs/dev_log.md)
