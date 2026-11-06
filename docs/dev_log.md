# Development Log - Team T060 (PS-115)

## 2026-11-03: Initial Project Setup & FAR Business Rule Implementation

### Objective
Establish a clean, modular Python project structure and implement the first core business rule: Floor Area Ratio (FAR) calculation and municipal compliance validation.

### Architecture Decisions
1. **Separation of Concerns**:
   - `src/far.py`: Pure business logic module with no UI or terminal dependencies. Functions accept numeric parameters and return clean numeric values or dictionaries.
   - `src/cli.py`: Interactive command-line interface layer responsible only for user prompts, formatting, and presenting results.
2. **Deterministic & Simple Code**:
   - Kept design strictly functional without unnecessary OOP classes or premature abstractions.
   - Used standard Python dictionaries for structured output, making the code easy to explain during viva examinations.
3. **Comprehensive Input Validation & Precision**:
   - Enforced strict checks: `plot_area > 0` (preventing division-by-zero or physical absurdity), `eligible_built_up_area >= 0`, `allowed_far >= 0`.
   - Explicitly rejected non-numeric inputs and booleans.
   - **Correctness Fix (Zero Tolerance for False Approvals)**: Removed premature rounding from `calculate_far()`. Compliance is strictly evaluated against the exact, unrounded FAR value so that slight overages (e.g. actual FAR 1.50004 against allowed 1.5000) are not masked into false compliance by rounding down.
4. **Automated Testing**:
   - Implemented unit tests using `pytest` in `tests/test_far.py`.
   - Verified normal calculations, edge cases (zero built-up area), boundary limits (FAR == allowed FAR), non-compliance (FAR > allowed FAR), and exception handling.

### Next Steps
- Implement Base FAR lookup based on building use and road width.

---

## 2026-11-03: Base FAR Lookup by Building Use and Road Width

### Objective
Implement municipal zoning table lookup to dynamically determine permitted base FAR based on building use (Residential, Commercial, Mixed Use) and abutting road width.

### Business Rules & Specifications
- **Residential**:
  - Road width < 12 m: FAR 1.75
  - Road width 12 m through 18 m (inclusive): FAR 2.25
  - Road width > 18 m: FAR 2.50
- **Commercial**:
  - Residential base FAR + 0.25 for corresponding road-width band.
- **Mixed Use**:
  - Equal to residential base FAR.

### Architecture Decisions
1. **New Function `get_base_far(building_use, road_width)`**:
   - Accepts building category and road width in metres.
   - Normalizes input strings (handles case sensitivity, whitespace, hyphens/underscores).
   - Validates that road width > 0 and building use is supported (`residential`, `commercial`, `mixed_use`).
   - Uses clear, readable conditionals (`width < 12.0`, `width <= 18.0`, else).
2. **Backwards Compatible Integration**:
   - `validate_far()` extended to accept either explicit `allowed_far` or `(building_use, road_width)`.
   - Existing tests remain 100% operational.
3. **Interactive CLI Updates**:
   - The CLI prompts user for building use and road width, automatically computes base FAR, and eliminates manual allowed FAR input.
4. **Comprehensive Test Suite**:
   - Added unit tests for all 3 road-width bands x 3 building uses (9 combinations).
   - Added explicit tests for exact boundary points (12.0 m, 18.0 m, 11.99 m, 18.01 m).
   - Added validation tests for negative/zero road widths and unsupported building uses.
   - Total test count expanded from 13 to 26 passing tests.

---

## 2026-11-04: Eligible Built-Up Area, Premium FAR, TDR, and Combined Cap

### Objectives
Implement Tasks 1, 2, and 3:
1. Deductions for eligible built-up area (stilt parking, basement parking, 10% balcony).
2. Premium FAR validation (max 0.5, road >= 12m) and rate/charge calculation (40% residential, 60% commercial).
3. Transferable Development Rights (TDR, max 0.4) and combined additional FAR cap (0.6 maximum additional FAR).
4. Full integration into `validate_far()` and the interactive CLI.

### Architectural Decisions & Ambiguity Handling
1. **Conceptual Separation of FAR Components**:
   - `base_far`: Looked up from road width and building use.
   - `premium_far`: Validated independently (must be <= 0.5 and road width >= 12m).
   - `tdr_far`: Validated independently (must be <= 0.4).
   - `combined_additional_far`: Validated against the combined cap of 0.6 (`premium_far + tdr_far <= 0.6`).
   - `final_permitted_far = base_far + combined_additional_far`.
   - Excess combinations (e.g. 0.5 + 0.4 = 0.9, excess 0.3) are explicitly rejected with `ValueError` and never silently altered.
2. **Eligible Built-up Area Logic**:
   - `calculate_eligible_built_up_area()` enforces `Total Built-up Area - Stilt - Basement - 0.10 * Balcony`.
   - Validates that total exclusions cannot exceed total built-up area.
3. **Ambiguity Identification in Premium FAR Charge**:
   - Specification specifies 40% for residential and 60% for commercial, but does not define mixed use. The engine rejects mixed use in `calculate_premium_far_rate()` with a clear error highlighting this ambiguity until official clarification is given.
   - Chargeable area for premium calculation is computed as `premium_far * plot_area`.
4. **Test Suite Expansion**:
   - Expanded from 26 to 51 passing automated tests in `tests/test_far.py`.
   - Validated exact boundaries: Premium 0.5, TDR 0.4, Road 12.0m, Combined Cap 0.6, and official 0.9 combination exceeding cap by 0.3.

---

## 2026-11-05: Official Dataset Integration & CSV Data Loader Module

### Objectives
1. Place official municipal data pack files into project under `data/` without modifying the original sample directory.
2. Implement `src/data_loader.py` using Python's standard `csv` library for typed parsing of zones, FAR tables, setbacks, coverage, fee schedules, applications, and floors.
3. Build robust interval-matching logic (`check_interval()`) respecting explicit inclusive/exclusive lower and upper bounds.
4. Add comprehensive unit tests in `tests/test_data_loader.py` covering type parsing, table loading, and boundary checks (total tests increased from 51 to 68).

---

## 2026-11-06: Milestone 2 — Municipal Fee Engine & Demand Calculation

### Objectives
1. Implement the complete municipal fee engine (`src/fees.py`) adhering to `fee_schedule.csv`, the PS-115 specification, and verified sample data.
2. Build calculation functions for all six fee components:
   - Scrutiny Fee (Rs 20/sq.m built-up, minimum Rs 2,000)
   - Development Charge (Residential Rs 300/sq.m, Commercial Rs 600/sq.m, Mixed-Use floor breakdown)
   - Premium FAR Fee (Chargeable area = premium FAR * plot area; 40% residential/mixed, 60% commercial)
   - Betterment Levy (2% of plot guidance value on agri-converted land)
   - Labour Welfare Cess (1% of construction cost @ Rs 1,800/sq.ft, 10.7639 sq.ft/sq.m)
   - Parking Shortfall Fee (Rs 200,000 per missing car for allowable shortfall <= 20%)
3. Implement `calculate_fee_demand(...)` assembling the exact `fee_demand.csv` schema with strict violation gating.
4. Verify every fee calculation against all 27 official `FEE_PAYMENT` records in `commands.txt`.

### Key Architectural Decisions & Evidence-Based Interpretations
1. **Per-Component Rounding Rule**:
   - Every individual fee component is rounded UP to the nearest Rs 10 (`ceil(fee / 10) * 10`).
   - `total_fee` is the exact sum of these rounded components. Verified across all 27 official payments with zero deviation.
2. **Floor-Level Mixed-Use Development Charge**:
   - Rather than applying a single blended rate across the building, the engine uses floor-level data from `floors.csv`. Commercial floors are charged at Rs 600/sq.m; residential, parking, stilt, and basement floors are charged at Rs 300/sq.m.
3. **Evidence-Based Interpretation — Mixed-Use Premium FAR Rate**:
   - *Status*: The official brief explicitly defines 40% guidance value for residential and 60% for commercial, but does not provide an explicit text formula for mixed use.
   - *Evidence*: Exhaustive audit of all 27 official payment records in `data/commands.txt` proved that mixed-use applications requesting premium FAR (e.g. APP-0008, APP-0040) calculate the fee using 40% of guidance value on `premium_far_requested * plot_area_sqm`. This yields a 100% exact rupee match.
   - *Documentation*: This rate is recorded strictly as an evidence-based interpretation derived from official sample data, and is not misrepresented as an explicit written regulation in the brief.
4. **Gating Rule**:
   - Applications with non-compoundable violations (e.g. zoning, coverage, height, parking > 20%, FAR cap) produce no fee demand (`calculate_fee_demand` returns `None`). Compoundable setback deviations (<= 0.3m) do not block fee demand generation.
5. **Testing & Verification**:
   - Created `tests/test_fees.py` with 27 unit and integration tests (total test suite expanded to 135 passing tests).
   - `test_all_27_official_fee_payments_match_exact_rupee` dynamically validates every initial fee payment in `commands.txt` with `diff == 0.0`.

---

## 2026-11-06: Milestone 3 — Statutory Workflow Engine & Lifecycle Tracking

### Objectives
1. Implement the municipal approval workflow engine (`src/workflow.py`) modeling statutory stage progressions:
   `SUBMITTED` -> `SCRUTINY` -> `SITE_INSPECTION` -> `TECHNICAL` -> `APPROVED` / `QUERY`
2. Implement municipal calendar math:
   - Monday-Friday working days excluding public holidays from `data/holidays.csv`.
   - Timer starts on the next working day after municipal fee payment.
   - Deemed approval triggered on the 46th running working day (exceeding 45 working days).
3. Implement query pauses and lifecycle rules:
   - Clock stopped during query; 30-calendar-day deadline.
   - 60-day lapse revival with 25% scrutiny fee.
   - 6-month commencement deadline, suspension, and Rs 5,000 revalidation.
   - One-time 1-year approval extension (10% fee) and rejection of second extension.
4. Execute and verify all 292 commands from `data/commands.txt`.

### Key Planted Scenarios Tested & Verified
1. **EC-07 Deemed Approval (APP-0001)**:
   - Fees paid Friday 2026-01-09 -> timer starts Monday 2026-01-12.
   - Skips Makara Sankranti (Jan 15) and Republic Day (Jan 26).
   - Clears Scrutiny (Jan 14) and Site Inspection (Feb 13).
   - Technical never decides -> 45 working days exceeded on Wednesday 2026-03-18 (46th working day) -> `DEEMED_APPROVED`.
2. **EC-06 Query Clock Resumption (APP-0019)**:
   - Technical issues Query on 2026-04-23.
   - Applicant responds on 2026-05-23 (30th calendar day) -> timer resumes; 30 clock-stopped days recorded.
   - Technical approves on 2026-06-02.
3. **Query Lapse and One-Time Revival (APP-0023)**:
   - Query issued 2026-05-05; 30-day response window expires -> lapses on 2026-06-05.
   - Revived on 2026-06-30 (25 days after lapse, within 60 days) with Rs 2,700 revival fee.
   - Query answered 2026-07-05, approved 2026-07-10. Second revival attempt rejected.
4. **Unpaid Fees Timer Gate (APP-0034)**:
   - Clean application where fees are never paid; timer never starts; no deemed approval.
5. **Commencement Deadline & Suspension (APP-0008)**:
   - Approved 2026-02-25; no commencement within 6 months -> suspended on 2026-08-25.
   - Revalidation fee of Rs 5,000 paid on 2026-09-06 -> revalidated; commencement on 2026-09-08.
6. **Extension Rules (APP-0011)**:
   - First extension on 2026-07-30 granted (1 year, 10% fee).
   - Second extension on 2026-09-08 rejected.
7. **Testing**:
   - Added `tests/test_workflow.py` with 12 comprehensive unit and integration tests.
   - Full test suite expanded to 147 passing tests.

---

## 2026-11-06: Milestone 4 — Completion Certificate (CC) & Deviation Compounding Engine

### Objectives
1. Implement the Completion Certificate evaluation and compounding module (`src/cc.py`) adhering to `fee_schedule.csv`, the PS-115 specification, and verified sample data.
2. Build calculation functions for as-built deviations:
   - Built-up area deviation slabs:
     - <= 5.0%: compounded at 2x development charge on excess area.
     - > 5.0% and <= 10.0%: compounded at 4x development charge on excess area.
     - > 10.0%: non-compoundable -> `CC_REFUSED`.
   - Setback deviation:
     - <= 0.30 m: compounded at Rs 10,000 per metre-side.
     - > 0.30 m: non-compoundable -> `CC_REFUSED`.
   - Height deviation:
     - > 0.0 m: strictly non-compoundable -> `CC_REFUSED`.
3. Implement `evaluate_cc_request(...)` emitting exact `cc_decisions.csv` schema:
   `app_id,request_date,deviation_pct,area_compounding_fee,setback_compounding_fee,height_deviation_m,decision`
4. Implement `process_cc_commands(...)` to process all `CC_REQUEST` commands from `data/commands.txt`.

### Verified Official Planted Cases
1. **APP-0013 (Height Deviation)**:
   - As-built height +0.40 m above approved 9.60 m -> `CC_REFUSED` (height is never compoundable).
2. **APP-0010 (Setback Compounding)**:
   - 0.30 m deviation on 2 sides -> `CC_ISSUED` with Rs 6,000 compounding fee ($10,000 \times 0.30 \times 2$).
3. **APP-0009 (5% Built-Up Slab)**:
   - Approved 273.00, as-built 286.65 (+5.00%) -> `CC_ISSUED` with 2x dev charge ($2 \times 300 \times 13.65 = \text{Rs 8,190.0}$).
4. **APP-0002 (Clean As-Built)**:
   - Matches approved -> `CC_ISSUED` with Rs 0 compounding fee.
5. **APP-0006 (Excess Built-Up > 10%)**:
   - Approved 609.18, as-built 682.28 (+12.00%) -> `CC_REFUSED` (exceeds 10% ceiling).
6. **APP-0007 (10% Built-Up Slab)**:
   - Approved 408.00, as-built 448.80 (+10.00%) -> `CC_ISSUED` with 4x dev charge ($4 \times 400 \times 40.80 = \text{Rs 65,280.0}$).

### Testing
- Created `tests/test_cc.py` with 11 comprehensive unit and integration tests.
- Full test suite expanded to 158 passing tests.

---

## 2026-11-06: Milestone 5 — End-to-End Command Runner & 4-CSV Output Generation

### Objectives
1. Implement the unified command pipeline runner (`src/runner.py`) executing all 292 commands from `data/commands.txt` strictly in original file order.
2. Implement statutory rule validation orchestrator (`validate_application`) evaluating all rules in canonical precedence order:
   `ZONING_USE` -> `FAR_BASE` / `FAR_PREMIUM` / `FAR_TDR` / `FAR_CAP` / `FAR_ACHIEVED` -> `GROUND_COVERAGE` -> `SETBACK_FRONT` / `SETBACK_SIDE1` / `SETBACK_SIDE2` / `SETBACK_REAR` -> `HEIGHT_LIMIT` -> `PARKING`.
3. Generate all four mandatory output files with exact column schemas and ordering:
   - `validation_report.csv` (40 rows: 12 violation rows sorted by app_id and precedence + 28 `NONE` rows).
   - `fee_demand.csv` (30 rows: fee breakdown for plans without non-compoundable violations; 10 fatal exclusions).
   - `workflow.csv` (76 stage transition rows logged in chronological date order).
   - `cc_decisions.csv` (6 rows: matching the 6 `CC_REQUEST` commands; 4 issued, 2 refused).
4. Build deterministic export capability to any designated target output directory.

### Testing & Verification
- Created `tests/test_runner.py` verifying:
  - Exact row counts, schemas, and sorting on all 4 CSV files.
  - Correct exclusion of the 10 fatal violation applications from `fee_demand.csv`.
  - Bitwise determinism across consecutive runs.
- Full automated test suite expanded to 162 passing tests.

---

## 2026-11-06: Milestone 6 — Submission Documentation, Design Document & Final Verification

### Objectives
1. Author comprehensive system design document (`docs/design_document.md`):
   - Municipal Domain Glossary with standard town planning definitions.
   - High-level Architectural Overview & Mermaid UML Class Diagram.
   - Statutory Workflow State Machine Diagram with stage transition rules.
   - Complete Business-Rule Register mapping rules to implementation modules and test files.
   - 19-point Ambiguity and Engineering Decision Log documenting evidence-based resolutions.
   - 5-Minute Live Demonstration Protocol and Viva Examination Preparation Guide.
2. Complete `README.md` with end-to-end architecture, quickstart commands, and planted test scenario results table.
3. Generate and verify all 4 deliverable CSV output files (`validation_report.csv`, `fee_demand.csv`, `workflow.csv`, `cc_decisions.csv`).
4. Execute full automated test suite (162 tests) and verify git tree integrity.
