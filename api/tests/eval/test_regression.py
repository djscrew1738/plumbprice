"""Pytest runner for the AI regression eval set.

These tests hit a live API at EVAL_BASE_URL (default
http://127.0.0.1:8200) and require:
  - the API service to be running
  - the eval user credentials to be valid

Set the env var `RUN_EVAL=1` to enable; otherwise the suite is skipped
(so unit-test CI doesn't pay the LLM round-trip cost).  Promote to
unconditional once a stable green is observed.
"""
from __future__ import annotations

import json
import os

import httpx
import pytest

from tests.eval import evaluate_response, load_cases

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_EVAL") != "1",
    reason="Set RUN_EVAL=1 to run AI regression eval (requires live API).",
)

BASE_URL = os.environ.get("EVAL_BASE_URL", "http://127.0.0.1:8200")
USERNAME = os.environ.get("EVAL_USERNAME", "cory.nich@outlook.com")
PASSWORD = os.environ.get("EVAL_PASSWORD", "admin1234")


@pytest.fixture(scope="module")
def auth_token() -> str:
    r = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.mark.parametrize("case", load_cases(), ids=lambda c: c["id"])
def test_regression_case(case: dict, auth_token: str) -> None:
    if case.get("xfail"):
        pytest.xfail(f"{case['id']} is a tracked classifier weakness")
    r = httpx.post(
        f"{BASE_URL}/api/v1/chat/price",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"message": case["message"]},
        timeout=90.0,
    )
    r.raise_for_status()
    result = evaluate_response(case, r.json())
    assert result.passed, (
        f"{result.case_id} failed:\n  - "
        + "\n  - ".join(result.failures)
        + f"\n  actual={json.dumps(result.actual, default=str)}"
    )
