from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from orchestrator.scoring import compute_overall_readiness
from preflight_schemas import AgentReview, ReadinessStatus


class ScoringTests(unittest.TestCase):
    def test_red_if_any_team_is_red(self) -> None:
        reviews = [
            AgentReview(team="engineering", readiness=ReadinessStatus.YELLOW),
            AgentReview(team="qa", readiness=ReadinessStatus.RED),
        ]
        self.assertEqual(compute_overall_readiness(reviews), ReadinessStatus.RED)

    def test_yellow_if_no_red_and_any_yellow(self) -> None:
        reviews = [
            AgentReview(team="engineering", readiness=ReadinessStatus.YELLOW),
            AgentReview(team="design", readiness=ReadinessStatus.GREEN),
        ]
        self.assertEqual(compute_overall_readiness(reviews), ReadinessStatus.YELLOW)

    def test_green_if_all_green(self) -> None:
        reviews = [
            AgentReview(team="engineering", readiness=ReadinessStatus.GREEN),
            AgentReview(team="qa", readiness=ReadinessStatus.GREEN),
        ]
        self.assertEqual(compute_overall_readiness(reviews), ReadinessStatus.GREEN)

    def test_green_if_empty_reviews(self) -> None:
        self.assertEqual(compute_overall_readiness([]), ReadinessStatus.GREEN)


if __name__ == "__main__":
    unittest.main()
