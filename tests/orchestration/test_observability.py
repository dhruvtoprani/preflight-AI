from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from orchestrator.engine import run_preflight
from orchestrator.observability import ObservabilitySink
from preflight_schemas import InitiativeBrief, ReviewObservabilityEvent


class InMemorySink(ObservabilitySink):
    def __init__(self) -> None:
        self.events: list[ReviewObservabilityEvent] = []

    def emit(self, event: ReviewObservabilityEvent) -> None:
        self.events.append(event)


class ObservabilityTests(unittest.TestCase):
    def test_run_preflight_emits_observability_event(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )
        sink = InMemorySink()

        run = run_preflight(brief, observability_sink=sink)

        self.assertEqual(len(sink.events), 1)
        event = sink.events[0]
        self.assertEqual(event.run_id, run.run_id)
        self.assertGreaterEqual(event.concern_count, 1)
        self.assertGreaterEqual(event.evidence_coverage, 0.0)
        self.assertLessEqual(event.evidence_coverage, 1.0)


if __name__ == "__main__":
    unittest.main()
