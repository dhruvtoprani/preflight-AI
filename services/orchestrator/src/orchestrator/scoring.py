from __future__ import annotations

from preflight_schemas import AgentReview, ReadinessStatus


def compute_overall_readiness(team_reviews: list[AgentReview]) -> ReadinessStatus:
    if not team_reviews:
        return ReadinessStatus.GREEN

    readiness_values = {review.readiness for review in team_reviews}

    if ReadinessStatus.RED in readiness_values:
        return ReadinessStatus.RED
    if ReadinessStatus.YELLOW in readiness_values:
        return ReadinessStatus.YELLOW
    return ReadinessStatus.GREEN
