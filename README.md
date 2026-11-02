# Municipal Building-Plan Approval Fee and FAR Compliance Engine

**Capstone Project**: Team T060  
**Problem Statement**: PS-115  
**Technology**: Python 3.10+, `pytest`, Command-Line Application (CLI)

---

## 1. Project Overview

This project implements an automated municipal compliance engine for building-plan approvals according to official PS-115 specifications.

### Core Business Rules Implemented

#### Rule 1: Floor Area Ratio (FAR) Calculation & Validation
- **Definition**: $\text{FAR} = \frac{\text{Eligible Built-Up Area}}{\text{Plot Area}}$
- **Compliance Condition**:
  - **COMPLIANT** if $\text{Calculated FAR} \le \text{Permitted FAR}$.
  - **NON-COMPLIANT** if $\text{Calculated FAR} > \text{Permitted FAR}$.
- **Precision Rule**: Evaluation is performed on exact mathematical ratios to prevent false positive approvals caused by rounding near boundary limits.

#### Rule 2: Base FAR Lookup by Building Use and Road Width
The permitted base FAR is determined automatically based on the abutting road width and the building use category:

| Abutting Road Width | Residential | Commercial (+0.25) | Mixed Use |
| :--- | :---: | :---: | :---: |
| **Below 12 m** (`< 12.0`) | **1.75** | **2.00** | **1.75** |
| **From 12 m through 18 m** (`12.0 <= width <= 18.0`) | **2.25** | **2.50** | **2.25** |
| **Above 18 m** (`> 18.0`) | **2.50** | **2.75** | **2.50** |

*Note: Mixed use adopts residential values. Commercial use receives a +0.25 bonus over the residential band.*

---

## 2. Project Directory Structure

```text
T060-PS-115/
├── .gitignore          # Ignores __pycache__, .pytest_cache, virtualenvs, etc.
├── README.md           # Project documentation and guide
├── requirements.txt    # Project dependencies (pytest)
├── docs/
│   └── dev_log.md      # Development and decision log
├── src/
│   ├── __init__.py     # Makes src a Python package
│   ├── far.py          # Core pure business logic for FAR
│   └── cli.py          # Interactive command-line interface
└── tests/
    ├── __init__.py     # Makes tests a package
    └── test_far.py     # Automated unit tests using pytest
```

---

## 3. Getting Started

### Prerequisites
- Python 3.10 or higher installed.

### Installation
Clone or navigate to the repository directory and install testing dependencies:

```bash
pip install -r requirements.txt
```

---

## 4. Running the Tests

To run the automated test suite with verbose output:

```bash
python -m pytest -v
```

This verifies:
1. Normal FAR calculations (e.g., plot = 1000, built-up = 1500 gives FAR 1.5).
2. Boundary cases (e.g., 0 built-up area, calculated FAR == allowed FAR).
3. Compliance rules (within limit vs exceeding limit).
4. Input validation (rejecting negative areas, zero plot area, negative allowed FAR, and non-numeric inputs).

---

## 5. Running the Interactive CLI

To run the interactive command-line tool:

```bash
python src/cli.py
```

### Example Usage:
```text
============================================================
Municipal Building-Plan Approval System: FAR Compliance Check
Team T060 | Problem Statement PS-115
============================================================

Select Building Use:
  1. Residential
  2. Commercial
  3. Mixed Use
Enter choice (1-3 or name): 1
Enter Abutting Road Width in metres: 12
  -> Permitted Base FAR: 2.2500

Enter Plot Area (sq. metres): 1000
Enter Eligible Built-up Area (sq. metres): 2000

------------------------------------------------------------
COMPLIANCE REPORT
------------------------------------------------------------
  Building Use           : Residential
  Road Width             : 12.00 m
  Permitted (Base) FAR   : 2.2500
  Plot Area              : 1000.00 sq.m
  Eligible Built-up Area : 2000.00 sq.m
  Calculated FAR         : 2
  Status                 : COMPLIANT
  Remarks                : FAR is within the permitted limit.
------------------------------------------------------------
```
