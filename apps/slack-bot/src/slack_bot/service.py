from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from preflight_schemas import InitiativeBrief, ReviewRun

from .formatter import format_thread_message
from .idempotency import IdempotencyStore
from .persistence import PersistResult, ReviewRunStore
from .slack_client import SlackMessenger


@dataclass
class ProcessResult:
    run: ReviewRun
    persisted: PersistResult
    thread_preview: str
    duplicate: bool


def _build_idempotency_key(brief: InitiativeBrief) -> str:
    # Stable key: requester+channel+thread+initiative payload hash.
    payload = json.dumps(brief.model_dump(), sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    base = f"{brief.channel_id or 'no-channel'}:{brief.thread_ts or 'no-thread'}:{brief.requester or 'no-requester'}"
    return f"{base}:{digest}"


def process_brief(
    brief: InitiativeBrief,
    review_runner,
    run_store: ReviewRunStore,
    idempotency_store: IdempotencyStore,
) -> ProcessResult:
    idem_key = _build_idempotency_key(brief)
    idem_result = idempotency_store.reserve(idem_key)
    if idem_result.is_duplicate:
        # Duplicate run: return a synthetic no-op from latest pipeline output not available.
        # We still generate a lightweight run for visibility.
        duplicate_run = review_runner(brief)
        preview = format_thread_message(duplicate_run)
        persisted = run_store.persist(duplicate_run)
        return ProcessResult(
            run=duplicate_run,
            persisted=persisted,
            thread_preview=preview,
            duplicate=True,
        )

    run = review_runner(brief)
    preview = format_thread_message(run)
    persisted = run_store.persist(run)
    return ProcessResult(run=run, persisted=persisted, thread_preview=preview, duplicate=False)


def run_review_and_notify(
    brief: InitiativeBrief,
    review_runner,
    messenger: SlackMessenger,
    run_store: ReviewRunStore,
    idempotency_store: IdempotencyStore,
) -> ProcessResult:
    channel = brief.channel_id
    thread_ts = brief.thread_ts

    if channel:
        messenger.post_message(
            channel=channel,
            thread_ts=thread_ts,
            text=(
                "PreFlight running review across relevant stakeholder lenses. "
                "I will post the synthesis shortly."
            ),
        )

    result = process_brief(
        brief=brief,
        review_runner=review_runner,
        run_store=run_store,
        idempotency_store=idempotency_store,
    )

    if channel:
        suffix = " (duplicate request detected)" if result.duplicate else ""
        messenger.post_message(
            channel=channel,
            thread_ts=thread_ts,
            text=f"{result.thread_preview}{suffix}",
        )

    return result
