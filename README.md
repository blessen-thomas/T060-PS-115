# Municipal Building-Plan Approval Fee and FAR Compliance Engine

**Capstone Project**: Team T060  
**Problem Statement**: PS-115  
**Technology**: Python 3.10+, `pytest`, Command-Line Application (CLI)

---

## 1. Project Overview

This project implements an automated municipal compliance engine for building-plan approvals. In this first phase, it implements **Rule 1: Floor Area Ratio (FAR) Calculation and Compliance Check**.

### What is FAR?
**Floor Area Ratio (FAR)** is a zoning metric that regulates the density and bulk of buildings. It is defined as:

$$\text{FAR} = \frac{\text{Eligible Built-Up Area}}{\text{Plot Area}}$$

A building plan is:
- **Compliant** if $\text{Calculated FAR} \le \text{Permitted (Allowed) FAR}$.
- **Non-Compliant** if $\text{Calculated FAR} > \text{Permitted (Allowed) FAR}$.

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

Enter Plot Area (sq. metres): 1200
Enter Eligible Built-up Area (sq. metres): 1800
Enter Allowed FAR limit (e.g., 1.5, 2.0): 1.5

------------------------------------------------------------
COMPLIANCE REPORT
------------------------------------------------------------
  Plot Area              : 1200.00 sq.m
  Eligible Built-up Area : 1800.00 sq.m
  Permitted (Allowed) FAR: 1.5000
  Calculated FAR         : 1.5000
  Status                 : COMPLIANT
  Remarks                : FAR is within the permitted limit.
------------------------------------------------------------
```
