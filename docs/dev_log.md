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
