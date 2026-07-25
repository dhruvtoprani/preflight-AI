from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATHS = [
    ROOT / "packages/schemas/src",
    ROOT / "packages/shared-utils/src",
    ROOT / "services/orchestrator/src",
    ROOT / "services/ingestion/src",
    ROOT / "services/retrieval/src",
]

for src_path in reversed(SRC_PATHS):
    src_string = str(src_path)
    if src_string not in sys.path:
        sys.path.insert(0, src_string)

from orchestrator.main import review  # noqa: E402
from preflight_schemas import InitiativeBrief  # noqa: E402

DEMO_BRIEF_DIR = ROOT / "docs" / "pilot" / "demo_briefs"


def _scenarios() -> list[InitiativeBrief]:
    scenario_paths = sorted(DEMO_BRIEF_DIR.glob("*.json"))
    if not scenario_paths:
        raise FileNotFoundError(f"No demo briefs found in {DEMO_BRIEF_DIR}")

    scenarios: list[InitiativeBrief] = []
    for scenario_path in scenario_paths:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenarios.append(InitiativeBrief.model_validate(payload))
    return scenarios


def _concern_metrics(run) -> tuple[int, int]:
    total = 0
    evidence_backed = 0
    for team_review in run.team_reviews:
        for concern in team_review.concerns:
            total += 1
            if concern.evidence_status.value == "evidence-backed":
                evidence_backed += 1
    return total, evidence_backed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal pilot evaluation over fixed scenarios.")
    parser.add_argument("--output", type=str, default="", help="Optional output JSON path")
    parser.add_argument(
        "--min-evidence-ratio",
        type=float,
        default=None,
        help="Optional threshold [0.0-1.0]. Exit 1 when evidence_backed_ratio is below this value.",
    )
    args = parser.parse_args()

    if args.min_evidence_ratio is not None and not 0.0 <= args.min_evidence_ratio <= 1.0:
        raise SystemExit("--min-evidence-ratio must be between 0.0 and 1.0")

    cases = _scenarios()
    runs = []
    readiness_counts = {"green": 0, "yellow": 0, "red": 0}
    total_concerns = 0
    total_evidence_backed = 0

    started = time.perf_counter()
    for case in cases:
        case_start = time.perf_counter()
        result = review(case)
        elapsed_ms = int((time.perf_counter() - case_start) * 1000)

        concern_count, evidence_backed_count = _concern_metrics(result)
        total_concerns += concern_count
        total_evidence_backed += evidence_backed_count

        readiness = result.moderator_summary.overall_readiness.value
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1

        runs.append(
            {
                "run_id": result.run_id,
                "title": result.initiative_title,
                "overall_readiness": readiness,
                "team_count": len(result.team_reviews),
                "concern_count": concern_count,
                "evidence_backed_count": evidence_backed_count,
                "warning_count": len(result.moderator_summary.warnings),
                "elapsed_ms": elapsed_ms,
            }
        )

    total_elapsed_ms = int((time.perf_counter() - started) * 1000)
    coverage = 0.0
    if total_concerns > 0:
        coverage = total_evidence_backed / total_concerns

    payload = {
        "scenario_count": len(cases),
        "total_elapsed_ms": total_elapsed_ms,
        "readiness_counts": readiness_counts,
        "total_concerns": total_concerns,
        "total_evidence_backed": total_evidence_backed,
        "evidence_backed_ratio": round(coverage, 4),
        "runs": runs,
    }

    if args.min_evidence_ratio is not None:
        payload["threshold_gate"] = {
            "min_evidence_ratio": round(args.min_evidence_ratio, 4),
            "passed": coverage >= args.min_evidence_ratio,
        }

    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if args.min_evidence_ratio is not None and coverage < args.min_evidence_ratio:
        print(
            f"pilot_eval threshold failed: evidence_backed_ratio={coverage:.4f} < min={args.min_evidence_ratio:.4f}",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
