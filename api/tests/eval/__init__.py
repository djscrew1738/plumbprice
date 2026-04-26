"""Shared loader/runner for the locked AI regression eval set.

Used by both `pytest api/tests/eval/test_regression.py` and the CLI script
`api/scripts/run_eval.py`.  The same logic powers both so a CI run and a
manual pre-deploy sanity check produce identical results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

CASES_FILE = Path(__file__).parent / "cases.yaml"


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    message: str
    failures: list[str] = field(default_factory=list)
    actual: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    xfail: bool = False  # known-failing case; surfaced but doesn't fail CI


def load_cases() -> list[dict]:
    with CASES_FILE.open() as fh:
        data = yaml.safe_load(fh)
    return data.get("cases", [])


def _normalize_codes(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).upper() for v in value]
    return [str(value).upper()]


def evaluate_response(case: dict, response: dict) -> CaseResult:
    """Compare a /api/v1/chat/price response against a case's expectations."""
    expect = case.get("expect", {})
    failures: list[str] = []

    estimate = response.get("estimate") or {}
    line_items = estimate.get("line_items") or []

    # task_code/county/quantity live in trace_json on the labor or trip line.
    actual_task_code = ""
    actual_county = ""
    actual_quantity: Optional[int] = None
    for li in line_items:
        trace = li.get("trace_json") or {}
        if not actual_task_code:
            tc = trace.get("template_code") or trace.get("task_code")
            if tc:
                actual_task_code = str(tc).upper()
        if not actual_county:
            c = trace.get("county")
            if c:
                actual_county = str(c).title()
        if actual_quantity is None and li.get("line_type") == "labor":
            q = li.get("quantity")
            if q is not None:
                try:
                    actual_quantity = int(q)
                except (TypeError, ValueError):
                    pass

    # Fallbacks to top-level template_used / response confidence
    if not actual_task_code:
        tu = response.get("template_used") or estimate.get("task_code")
        if tu:
            actual_task_code = str(tu).upper()

    actual_total = estimate.get("grand_total")
    actual_confidence = response.get("confidence") or estimate.get("confidence")

    expected_codes = _normalize_codes(expect.get("task_code"))
    if expected_codes and actual_task_code not in expected_codes:
        failures.append(
            f"task_code: expected one of {expected_codes}, got {actual_task_code!r}"
        )

    expected_county = expect.get("county")
    if expected_county:
        expected_counties = (
            [str(c).title() for c in expected_county]
            if isinstance(expected_county, list)
            else [str(expected_county).title()]
        )
        if actual_county not in expected_counties:
            failures.append(f"county: expected one of {expected_counties}, got {actual_county!r}")

    min_price = expect.get("min_price")
    max_price = expect.get("max_price")
    if min_price is not None and (actual_total is None or actual_total < min_price):
        failures.append(f"grand_total {actual_total} below floor {min_price}")
    if max_price is not None and (actual_total is None or actual_total > max_price):
        failures.append(f"grand_total {actual_total} above ceiling {max_price}")

    min_conf = expect.get("min_confidence")
    if min_conf is not None and (actual_confidence is None or actual_confidence < min_conf):
        failures.append(
            f"confidence {actual_confidence} below floor {min_conf}"
        )

    expected_qty = expect.get("quantity")
    if expected_qty is not None and actual_quantity != expected_qty:
        failures.append(f"quantity: expected {expected_qty}, got {actual_quantity}")

    actual = {
        "task_code": actual_task_code,
        "county": actual_county,
        "grand_total": actual_total,
        "quantity": actual_quantity,
        "confidence": actual_confidence,
    }
    return CaseResult(
        case_id=case["id"],
        passed=not failures,
        message=case["message"],
        failures=failures,
        actual=actual,
        expected=expect,
        xfail=bool(case.get("xfail", False)),
    )


def format_report(results: list[CaseResult]) -> str:
    lines = []
    passed = sum(1 for r in results if r.passed)
    xfailed = sum(1 for r in results if not r.passed and r.xfail)
    hard_failed = sum(1 for r in results if not r.passed and not r.xfail)
    total = len(results)
    lines.append(
        f"AI Regression Eval — {passed}/{total} passed, "
        f"{hard_failed} failed, {xfailed} xfail"
    )
    lines.append("=" * 60)
    for r in results:
        if r.passed:
            marker = "PASS"
        elif r.xfail:
            marker = "XFAIL"
        else:
            marker = "FAIL"
        lines.append(f"[{marker}] {r.case_id}")
        if not r.passed:
            for f in r.failures:
                lines.append(f"     - {f}")
            lines.append(f"     actual={r.actual}")
    return "\n".join(lines)
