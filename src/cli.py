"""Command-Line Interface for the FAR Compliance Engine.

Allows the user to interactively enter:
1. Building use (Residential, Commercial, Mixed Use)
2. Abutting road width (metres)
3. Optional Additional FAR: Premium FAR (up to 0.5) and TDR (up to 0.4)
4. Plot area (sq. metres)
5. Built-up area breakdown (Total, Stilt Parking, Basement Parking, Balcony)

The engine automatically:
- Determines base FAR from municipal road-width zoning rules.
- Validates Premium FAR and TDR, enforcing the combined 0.6 cap.
- Calculates premium FAR charges based on guidance values.
- Computes eligible built-up area after exclusions.
- Evaluates compliance and prints a comprehensive report.
"""

import sys
import os

# Ensure project root is in Python module search path when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.far import (
    calculate_eligible_built_up_area,
    calculate_premium_far_charge,
    get_base_far,
    validate_far,
)


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


def prompt_float_default(prompt_text: str, default: float = 0.0) -> float:
    """Prompt the user for a number, returning default if user presses Enter."""
    while True:
        raw_val = input(prompt_text).strip()
        if not raw_val:
            return default
        try:
            return float(raw_val)
        except ValueError:
            print(f"  Error: Please enter a valid number or press Enter for {default}.")


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
    print("=" * 65)
    print("Municipal Building-Plan Approval System: FAR Compliance Check")
    print("Team T060 | Problem Statement PS-115")
    print("=" * 65)
    print()

    try:
        # 1. Building Use & Road Width -> Base FAR
        building_use = prompt_building_use()
        road_width = prompt_float("Enter Abutting Road Width in metres: ")
        base_far = get_base_far(building_use, road_width)
        print(f"  -> Permitted Base FAR: {base_far:.4f}\n")

        # 2. Additional FAR (Premium & TDR)
        print("Additional FAR (optional, press Enter for 0):")
        premium_far = prompt_float_default("  Enter requested Premium FAR (max 0.5, road >= 12m) [0]: ", 0.0)
        tdr_far = prompt_float_default("  Enter requested TDR FAR (max 0.4) [0]: ", 0.0)

        premium_charge_info = None
        if premium_far > 0 and building_use in ("residential", "commercial"):
            guidance_val = prompt_float("  Enter Guidance Value per sq.m for premium calculation: ")
        else:
            guidance_val = 0.0

        # 3. Plot Area & Built-up Area
        print()
        plot_area = prompt_float("Enter Plot Area (sq. metres): ")

        print("\nBuilt-up Area Details:")
        use_deductions = input("  Do you want to specify area exclusions (parking, balcony)? (y/n) [n]: ").strip().lower()

        if use_deductions in ("y", "yes"):
            total_built_up = prompt_float("  Enter Total Built-up Area (sq. metres): ")
            stilt = prompt_float_default("  Enter Stilt Parking Area (sq.m, 100% excluded) [0]: ", 0.0)
            basement = prompt_float_default("  Enter Basement Parking Area (sq.m, 100% excluded) [0]: ", 0.0)
            balcony = prompt_float_default("  Enter Balcony Area (sq.m, 10% excluded) [0]: ", 0.0)

            eligible_area = calculate_eligible_built_up_area(
                total_built_up_area=total_built_up,
                stilt_parking_area=stilt,
                basement_parking_area=basement,
                balcony_area=balcony,
            )
            print(f"  -> Calculated Eligible Built-up Area: {eligible_area:.2f} sq.m\n")

            result = validate_far(
                plot_area=plot_area,
                total_built_up_area=total_built_up,
                stilt_parking_area=stilt,
                basement_parking_area=basement,
                balcony_area=balcony,
                building_use=building_use,
                road_width=road_width,
                premium_far=premium_far,
                tdr_far=tdr_far,
            )
        else:
            eligible_area = prompt_float("  Enter Eligible Built-up Area (sq. metres): ")
            result = validate_far(
                plot_area=plot_area,
                eligible_built_up_area=eligible_area,
                building_use=building_use,
                road_width=road_width,
                premium_far=premium_far,
                tdr_far=tdr_far,
            )

        if premium_far > 0 and building_use in ("residential", "commercial") and guidance_val > 0:
            premium_charge_info = calculate_premium_far_charge(
                premium_far=premium_far,
                plot_area=plot_area,
                building_use=building_use,
                guidance_value=guidance_val,
            )

        use_display = {
            "residential": "Residential",
            "commercial": "Commercial",
            "mixed_use": "Mixed Use",
        }.get(building_use, building_use)

        print()
        print("-" * 65)
        print("COMPLIANCE & APPROVAL REPORT")
        print("-" * 65)
        print(f"  Building Use               : {use_display}")
        print(f"  Abutting Road Width        : {result['road_width']:.2f} m")
        print(f"  Plot Area                  : {result['plot_area']:.2f} sq.m")
        if result["total_built_up_area"] is not None:
            print(f"  Total Built-up Area        : {result['total_built_up_area']:.2f} sq.m")
        print(f"  Eligible Built-up Area     : {result['eligible_built_up_area']:.2f} sq.m")
        print(f"  Base FAR                   : {result['base_far']:.4f}")
        print(f"  Premium FAR                : {result['premium_far']:.4f}")
        print(f"  TDR FAR                    : {result['tdr_far']:.4f}")
        print(f"  Final Permitted FAR        : {result['allowed_far']:.4f}")
        print(f"  Calculated Proposed FAR    : {result['calculated_far']:.6g}")
        print(f"  Compliance Status          : {'COMPLIANT' if result['is_compliant'] else 'NON-COMPLIANT'}")
        print(f"  Remarks                    : {result['message']}")

        if premium_charge_info:
            print("-" * 65)
            print("PREMIUM FAR CHARGES")
            print("-" * 65)
            print(f"  Guidance Value             : {premium_charge_info['guidance_value']:.2f} / sq.m")
            print(f"  Charge Rate ({int(premium_charge_info['rate_percentage'] * 100)}%)      : {premium_charge_info['rate_per_sqm']:.2f} / sq.m")
            print(f"  Chargeable Additional Area : {premium_charge_info['chargeable_area']:.2f} sq.m")
            print(f"  Total Premium FAR Fee      : {premium_charge_info['total_charge']:.2f}")

        print("-" * 65)

    except ValueError as err:
        print()
        print(f"Validation Error: {err}")
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")


if __name__ == "__main__":
    main()
