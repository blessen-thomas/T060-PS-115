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
3. **Comprehensive Input Validation**:
   - Enforced strict checks: `plot_area > 0` (preventing division-by-zero or physical absurdity), `eligible_built_up_area >= 0`, `allowed_far >= 0`.
   - Explicitly rejected non-numeric inputs and booleans.
4. **Automated Testing**:
   - Implemented unit tests using `pytest` in `tests/test_far.py`.
   - Verified normal calculations, edge cases (zero built-up area), boundary limits (FAR == allowed FAR), non-compliance (FAR > allowed FAR), and exception handling.

### Next Steps
- Review with team/supervisor.
- Once approved, commit initial structure to Git.
- Prepare for subsequent business rules (e.g., fee calculation or zoning lookup tables according to PS-115 specifications).
