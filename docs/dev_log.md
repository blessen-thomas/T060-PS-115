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
