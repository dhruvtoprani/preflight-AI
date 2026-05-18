from __future__ import annotations

import time
from uuid import uuid4

from preflight_schemas import InitiativeBrief, ReviewRun

from .moderator import Moderator, build_default_moderator
from .observability import (
    JsonlObservabilitySink,
    ObservabilitySink,
    build_review_observability_event,
)
from .runners import AgentRunner, DeterministicRunner


def run_preflight(
    brief: InitiativeBrief,
    runner: AgentRunner | None = None,
    moderator: Moderator | None = None,
    observability_sink: ObservabilitySink | None = None,
) -> ReviewRun:
    """Run a preflight review with pluggable runner + moderator layers."""

    started = time.perf_counter()
    active_runner: AgentRunner = runner or DeterministicRunner()
    active_moderator: Moderator = moderator or build_default_moderator()

    runner_result = active_runner.run(brief)
    summary = active_moderator.summarize(
        brief=brief,
        team_reviews=runner_result.team_reviews,
        warnings=runner_result.warnings,
    )

    run = ReviewRun(
        run_id=str(uuid4()),
        initiative_title=brief.title,
        requester=brief.requester,
        channel_id=brief.channel_id,
        thread_ts=brief.thread_ts,
        team_reviews=runner_result.team_reviews,
        moderator_summary=summary,
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    sink = observability_sink or JsonlObservabilitySink()
    sink.emit(build_review_observability_event(run, elapsed_ms=elapsed_ms))

    return run
