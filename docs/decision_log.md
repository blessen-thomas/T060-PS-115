# PS-115 Engineering Decision Log

**Project:** Municipal Building-Plan Approval Fee and FAR Compliance Engine  
**Team ID:** T060  
**Problem Statement:** PS-115  

---

## 1. Technology and Architecture

- **D-01: Adoption of Python 3.10+ Standard Library** — Python 3.10+ provides robust built-in typing, date math, and CSV parsing modules while avoiding external runtime dependencies for standard municipal evaluation.
- **D-02: CLI and File-Driven Backend Architecture** — The engine is designed as a headless command-line and batch pipeline without a web frontend to prioritize municipal rule fidelity, determinism, and automated scriptability.
- **D-03: Modular Domain Separation** — Core functionality is separated into dedicated domain modules (`data_loader.py`, `far.py`, `rules.py`, `fees.py`, `workflow.py`, `cc.py`, and `runner.py`) to isolate regulatory responsibilities and simplify maintenance.
- **D-04: Pytest as Sole Development Dependency** — Automated unit and integration testing relies solely on `pytest` to maintain a lightweight environment without complex testing frameworks.

---

## 2. Data and Processing

- **D-05: Standard CSV Format for Tabular Inputs and Outputs** — All regulatory tables, applications, floor plans, and generated reports use comma-separated values (CSV) for portability, spreadsheet accessibility, and evaluation compliance.
- **D-06: Strict In-Order Command Stream Processing** — Application commands from `commands.txt` are executed strictly in sequential file order to maintain statutory timeline integrity across workflow transitions.
- **D-07: Immutability of Original Municipal Datasets** — The official source data in `data/` is treated as immutable, with all pipeline runs reading from repository data copies and exporting to configurable output directories.
- **D-08: Explicit Half-Open and Closed Interval Lookups** — Regulatory lookup tables for FAR, setbacks, and coverage use explicit boolean flags (`from_inclusive`, `to_inclusive`) to prevent boundary ambiguity.

---

## 3. Business Logic

- **D-09: Unrounded Floating-Point Comparisons for Plan Compliance** — Compliance checking retains full floating-point precision rather than premature rounding to eliminate false approvals on marginal overages.
- **D-10: Statutory Rule Precedence Hierarchy** — Plan validation evaluates rules in strict statutory order (`ZONING_USE` $\rightarrow$ `FAR` $\rightarrow$ `GROUND_COVERAGE` $\rightarrow$ `SETBACKS` $\rightarrow$ `HEIGHT_LIMIT` $\rightarrow$ `PARKING`) to flag fundamental zoning and density defects first.
- **D-11: Gating Fee Demands on Non-Compoundable Violations** — Applications with fatal, non-compoundable scrutiny violations are excluded from `fee_demand.csv` to prevent revenue assessment on unapprovable plans.
- **D-12: Component-Wise Rounding Up to Nearest ₹10** — Each statutory fee component is rounded up to the nearest ₹10 independently, with total fees derived as the exact sum of these rounded components.
- **D-13: Calendar Math with Gazetted Holiday Exclusion** — Working days strictly exclude Saturdays, Sundays, and public holidays listed in `holidays.csv`, commencing on the next municipal working day following fee payment.
- **D-14: Query Clock Suspension and Lapse Mechanics** — Issuing a query halts the working-day workflow timer, enforcing a 30-calendar-day response window, a 60-calendar-day lapse recovery window, and a 25% scrutiny fee revival penalty.
- **D-15: Strict Non-Compounding for Height Deviations** — As-built height overages ($> 0.0\text{ m}$) are classified as strictly non-compoundable, triggering completion certificate refusal (`CC_REFUSED`) without fee regularisation.
- **D-16: Discrete Completion Certificate Evaluation Engine** — As-built completion certificate (CC) requests are evaluated in an isolated subsystem comparing approved against as-built parameters for area, setback, and height tolerances.

---

## 4. Testing and Output Design

- **D-17: Fixed Column Schemas and Output Determinism** — All four generated reports (`validation_report.csv`, `fee_demand.csv`, `workflow.csv`, and `cc_decisions.csv`) conform to the exact evaluation column order, sorting criteria, and numeric formatting.
- **D-18: Planted Edge-Case Verification Without Hardcoded Branching** — Planted municipal edge cases (such as 12m road boundaries, 200 sqm coverage thresholds, and 20% parking shortfall limits) are verified via general business rules rather than hardcoded application IDs.

