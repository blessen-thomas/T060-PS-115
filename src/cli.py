"""Command-Line Interface for the FAR Compliance Engine.

Allows the user to interactively enter:
1. Plot area
2. Eligible built-up area
3. Allowed FAR

It then computes the FAR and reports whether the building plan is compliant.
"""

import sys
import os

# Ensure project root is in Python module search path when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.far import validate_far


def prompt_float(prompt_text: str) -> float:
    """Prompt the user for a floating-point number until valid input is given.

    Exits gracefully if user sends EOF (Ctrl+D / Ctrl+Z) or keyboard interrupt (Ctrl+C).
    """
    while True:
        try:
            raw_val = input(prompt_text).strip()
            return float(raw_val)
        except ValueError:
            print("  Error: Please enter a valid number (e.g., 1000 or 1500.5).")


def main() -> None:
    """Run the interactive FAR compliance check."""
    print("=" * 60)
    print("Municipal Building-Plan Approval System: FAR Compliance Check")
    print("Team T060 | Problem Statement PS-115")
    print("=" * 60)
    print()

    try:
        plot_area = prompt_float("Enter Plot Area (sq. metres): ")
        built_up_area = prompt_float("Enter Eligible Built-up Area (sq. metres): ")
        allowed_far = prompt_float("Enter Allowed FAR limit (e.g., 1.5, 2.0): ")

        result = validate_far(
            plot_area=plot_area,
            eligible_built_up_area=built_up_area,
            allowed_far=allowed_far,
        )

        print()
        print("-" * 60)
        print("COMPLIANCE REPORT")
        print("-" * 60)
        print(f"  Plot Area              : {result['plot_area']:.2f} sq.m")
        print(f"  Eligible Built-up Area : {result['eligible_built_up_area']:.2f} sq.m")
        print(f"  Permitted (Allowed) FAR: {result['allowed_far']:.4f}")
        print(f"  Calculated FAR         : {result['calculated_far']:.4f}")
        print(f"  Status                 : {'COMPLIANT' if result['is_compliant'] else 'NON-COMPLIANT'}")
        print(f"  Remarks                : {result['message']}")
        print("-" * 60)

    except ValueError as err:
        print()
        print(f"Validation Error: {err}")
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")


if __name__ == "__main__":
    main()
