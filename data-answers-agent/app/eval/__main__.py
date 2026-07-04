"""CLI entry: python -m app.eval"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.eval.harness import run_golden_eval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run golden-set evaluation harness")
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Path to golden_set.yaml (default: eval/golden_set.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full report as JSON",
    )
    args = parser.parse_args(argv)

    report = run_golden_eval(golden_path=args.golden)

    if args.json:
        print(json.dumps(report.model_dump(), indent=2))
    else:
        print(f"Golden eval: {report.passed}/{report.total} passed")
        print(f"  deflection_rate:     {report.deflection_rate:.2%}")
        print(f"  clarification_rate:  {report.clarification_rate:.2%}")
        print(f"  decline_rate:        {report.decline_rate:.2%}")
        for case in report.cases:
            mark = "PASS" if case.passed else "FAIL"
            print(f"  [{mark}] {case.case_id} (expected {case.expected_status}, got {case.actual_status})")
            for failure in case.failures:
                print(f"         - {failure}")

    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
