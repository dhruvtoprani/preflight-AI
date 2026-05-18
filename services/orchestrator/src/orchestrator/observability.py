from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

from preflight_schemas import ReviewObservabilityEvent, ReviewRun


class ObservabilitySink(Protocol):
    def emit(self, event: ReviewObservabilityEvent) -> None:
        """Emit one observability event."""


class JsonlObservabilitySink:
    def __init__(self, output_path: Path | None = None) -> None:
        default_base = Path(tempfile.gettempdir()) / "preflight-ai"
        self.output_path = output_path or default_base / "review_events.jsonl"

    def emit(self, event: ReviewObservabilityEvent) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(event.model_dump_json())
            file_obj.write("\n")


def build_review_observability_event(
    run: ReviewRun,
    elapsed_ms: int,
) -> ReviewObservabilityEvent:
    concerns = [concern for review in run.team_reviews for concern in review.concerns]
    concern_count = len(concerns)

    if concern_count == 0:
        evidence_coverage = 1.0
        avg_confidence = 1.0
    else:
        evidence_coverage = sum(1 for concern in concerns if concern.evidence) / concern_count
        avg_confidence = sum(concern.confidence for concern in concerns) / concern_count

    return ReviewObservabilityEvent(
        run_id=run.run_id,
        initiative_title=run.initiative_title,
        overall_readiness=run.moderator_summary.overall_readiness.value,
        elapsed_ms=elapsed_ms,
        team_count=len(run.team_reviews),
        concern_count=concern_count,
        warning_count=len(run.moderator_summary.warnings),
        evidence_coverage=round(evidence_coverage, 4),
        avg_confidence=round(avg_confidence, 4),
    )
