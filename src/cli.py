"""Command-Line Interface for the FAR Compliance Engine.

Allows the user to interactively enter:
1. Building use (Residential, Commercial, Mixed Use)
2. Abutting road width (metres)
3. Plot area (sq. metres)
4. Eligible built-up area (sq. metres)

The engine automatically determines permitted base FAR from zoning rules,
computes proposed FAR, and reports compliance.
"""

import sys
import os

# Ensure project root is in Python module search path when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.far import get_base_far, validate_far


def prompt_float(prompt_text: str) -> float:
    """Prompt the user for a floating-point number until valid input is given.

    Exits gracefully if user sends EOF (Ctrl+D / Ctrl+Z) or keyboard interrupt (Ctrl+C).
    """
    while True:
        try:
            raw_val = input(prompt_text).strip()
            return float(raw_val)
        except ValueError:
            print("  Error: Please enter a valid number (e.g., 1000 or 12.5).")


def prompt_building_use() -> str:
    """Prompt the user to select or enter a valid building use category."""
    print("Select Building Use:")
    print("  1. Residential")
    print("  2. Commercial")
    print("  3. Mixed Use")

    mapping = {
        "1": "residential",
        "2": "commercial",
        "3": "mixed_use",
        "residential": "residential",
        "commercial": "commercial",
        "mixed use": "mixed_use",
        "mixed_use": "mixed_use",
    }
    while True:
        choice = input("Enter choice (1-3 or name): ").strip().lower()
        if choice in mapping:
            return mapping[choice]
        print("  Error: Please enter 1, 2, 3, or a valid use (residential, commercial, mixed use).")


def main() -> None:
    """Run the interactive FAR compliance check."""
    print("=" * 60)
    print("Municipal Building-Plan Approval System: FAR Compliance Check")
    print("Team T060 | Problem Statement PS-115")
    print("=" * 60)
    print()

    try:
        building_use = prompt_building_use()
        road_width = prompt_float("Enter Abutting Road Width in metres: ")

        # Automatically determine permitted base FAR from building use and road width
        base_far = get_base_far(building_use, road_width)
        print(f"  -> Permitted Base FAR: {base_far:.4f}\n")

        plot_area = prompt_float("Enter Plot Area (sq. metres): ")
        built_up_area = prompt_float("Enter Eligible Built-up Area (sq. metres): ")

        result = validate_far(
            plot_area=plot_area,
            eligible_built_up_area=built_up_area,
            allowed_far=base_far,
            building_use=building_use,
            road_width=road_width,
        )

        use_display = {
            "residential": "Residential",
            "commercial": "Commercial",
            "mixed_use": "Mixed Use",
        }.get(building_use, building_use)

        print()
        print("-" * 60)
        print("COMPLIANCE REPORT")
        print("-" * 60)
        print(f"  Building Use           : {use_display}")
        print(f"  Road Width             : {result['road_width']:.2f} m")
        print(f"  Permitted (Base) FAR   : {result['allowed_far']:.4f}")
        print(f"  Plot Area              : {result['plot_area']:.2f} sq.m")
        print(f"  Eligible Built-up Area : {result['eligible_built_up_area']:.2f} sq.m")
        print(f"  Calculated FAR         : {result['calculated_far']:.6g}")
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
