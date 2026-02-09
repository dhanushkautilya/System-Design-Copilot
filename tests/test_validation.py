import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from pydantic import ValidationError
from backend.schemas import InputPayload


def valid_payload():
    return dict(
        app_name="TestApp",
        description="desc",
        dau=1000,
        peak_rps=50,
        read_write_ratio=3,
        regions=["us-east"],
        budget_level="medium",
        domain="fintech", # Optional but included here
        traffic_pattern="steady",
    )


def test_invalid_budget():
    data = valid_payload()
    data["budget_level"] = "ultra"
    with pytest.raises(ValidationError):
        InputPayload(**data)


def test_invalid_traffic_pattern():
    data = valid_payload()
    data["traffic_pattern"] = "erratic"
    with pytest.raises(ValidationError):
        InputPayload(**data)
