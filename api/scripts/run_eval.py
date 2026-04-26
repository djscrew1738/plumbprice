"""CLI: run the AI regression eval set against a live API.

Usage (from repo root):

    cd api && source .venv/bin/activate
    python scripts/run_eval.py \
        --base-url http://127.0.0.1:8200 \
        --username cory.nich@outlook.com \
        --password admin1234

Exits with status code 0 on full pass, 1 on any failure.  Writes a JSON
report to `tests/eval/last_run.json` for trend tracking.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.eval import (  # noqa: E402
    CaseResult,
    evaluate_response,
    format_report,
    load_cases,
)


async def _login(client: httpx.AsyncClient, base_url: str, username: str, password: str) -> str:
    r = await client.post(
        f"{base_url}/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def _run_case(client: httpx.AsyncClient, base_url: str, token: str, case: dict) -> CaseResult:
    try:
        r = await client.post(
            f"{base_url}/api/v1/chat/price",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": case["message"]},
            timeout=90.0,
        )
        r.raise_for_status()
        body = r.json()
    except Exception as exc:
        return CaseResult(
            case_id=case["id"],
            passed=False,
            message=case["message"],
            failures=[f"request failed: {exc}"],
        )
    return evaluate_response(case, body)


async def _amain(args: argparse.Namespace) -> int:
    cases = load_cases()
    if not cases:
        print("No cases found.", file=sys.stderr)
        return 1

    async with httpx.AsyncClient() as client:
        token = await _login(client, args.base_url, args.username, args.password)
        results: list[CaseResult] = []
        for case in cases:
            result = await _run_case(client, args.base_url, token, case)
            marker = "PASS" if result.passed else "FAIL"
            print(f"[{marker}] {result.case_id}")
            if not result.passed:
                for f in result.failures:
                    print(f"     - {f}")
            results.append(result)

    print()
    print(format_report(results))

    out_path = REPO_ROOT / "tests" / "eval" / "last_run.json"
    out_path.write_text(
        json.dumps(
            {
                "passed": sum(1 for r in results if r.passed),
                "total": len(results),
                "results": [
                    {
                        "case_id": r.case_id,
                        "passed": r.passed,
                        "failures": r.failures,
                        "actual": r.actual,
                        "expected": r.expected,
                    }
                    for r in results
                ],
            },
            indent=2,
        )
    )
    print(f"\nReport written to {out_path}")
    # Hard-fail only on cases that aren't marked xfail.
    hard_failures = [r for r in results if not r.passed and not r.xfail]
    return 0 if not hard_failures else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Run PlumbPrice AI regression eval set.")
    p.add_argument("--base-url", default=os.environ.get("EVAL_BASE_URL", "http://127.0.0.1:8200"))
    p.add_argument("--username", default=os.environ.get("EVAL_USERNAME", "cory.nich@outlook.com"))
    p.add_argument("--password", default=os.environ.get("EVAL_PASSWORD", "admin1234"))
    args = p.parse_args()
    sys.exit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
