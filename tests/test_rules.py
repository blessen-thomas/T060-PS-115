"""Unit Tests for Municipal Rule Validation Engine (src/rules.py)."""

from pathlib import Path
import pytest

from src.data_loader import load_applications, load_zones
from src.rules import check_zoning_use

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def zones():
    """Load the official zones table from data/zones.csv."""
    return load_zones(DATA_DIR / "zones.csv")


@pytest.fixture
def applications():
    """Load official applications from data/applications.csv."""
    return load_applications(DATA_DIR / "applications.csv")


# ==============================================================================
# 1. Zoning & Permitted Use Validation Tests (ZONING_USE)
# ==============================================================================

def test_check_zoning_use_permitted_passes(zones):
    """Permitted use in zone should pass validation."""
    # ZN-R1 permits RESIDENTIAL
    result = check_zoning_use("ZN-R1", "RESIDENTIAL", zones)
    assert result["passed"] is True
    assert result["rule_id"] == "ZONING_USE"
    assert result["proposed"] == "RESIDENTIAL"
    assert result["required"] == "RESIDENTIAL"
    assert result["compoundable"] is False

    # ZN-C1 permits COMMERCIAL;MIXED
    result_comm = check_zoning_use("ZN-C1", "COMMERCIAL", zones)
    assert result_comm["passed"] is True

    result_mix = check_zoning_use("ZN-C1", "MIXED", zones)
    assert result_mix["passed"] is True


def test_check_zoning_use_violation_fails(zones):
    """Unpermitted use in zone should fail validation."""
    # ZN-R1 does NOT permit COMMERCIAL
    result = check_zoning_use("ZN-R1", "COMMERCIAL", zones)
    assert result["passed"] is False
    assert result["rule_id"] == "ZONING_USE"
    assert result["proposed"] == "COMMERCIAL"
    assert result["required"] == "RESIDENTIAL"
    assert result["compoundable"] is False


def test_check_zoning_use_unknown_zone_handled(zones):
    """Unknown zone ID is safely handled without unhandled crashes."""
    result = check_zoning_use("ZN-NONEXISTENT", "RESIDENTIAL", zones)
    assert result["passed"] is False
    assert "Unknown zone" in result["proposed"]

    # When raise_on_unknown_zone is requested, ValueError is raised
    with pytest.raises(ValueError, match="Unknown zone_id"):
        check_zoning_use("ZN-NONEXISTENT", "RESIDENTIAL", zones, raise_on_unknown_zone=True)


def test_check_zoning_use_app_0032_planted_case(zones, applications):
    """Official planted scenario: APP-0032 proposes COMMERCIAL in ZN-R1 (residential only).

    Must be reported as a non-compoundable ZONING_USE violation.
    """
    app_0032 = next(a for a in applications if a["app_id"] == "APP-0032")
    assert app_0032["zone_id"] == "ZN-R1"
    assert app_0032["proposed_use"] == "COMMERCIAL"

    result = check_zoning_use(app_0032["zone_id"], app_0032["proposed_use"], zones)
    assert result["passed"] is False
    assert result["rule_id"] == "ZONING_USE"
    assert result["proposed"] == "COMMERCIAL"
    assert result["required"] == "RESIDENTIAL"
    assert result["compoundable"] is False

