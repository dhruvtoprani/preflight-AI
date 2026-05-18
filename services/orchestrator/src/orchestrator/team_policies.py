from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TeamContextPolicy:
    team: str
    focus_areas: list[str]
    preferred_sources: list[str]
    retrieval_hints: list[str]


DEFAULT_TEAM_POLICIES: dict[str, TeamContextPolicy] = {
    "engineering": TeamContextPolicy(
        team="engineering",
        focus_areas=[
            "feasibility",
            "dependencies",
            "ownership",
            "technical debt",
            "team availability",
        ],
        preferred_sources=["jira", "confluence", "architecture_notes", "roadmap"],
        retrieval_hints=["api ownership", "dependency map", "capacity", "technical constraints"],
    ),
    "qa": TeamContextPolicy(
        team="qa",
        focus_areas=[
            "regression risk",
            "test coverage",
            "environment readiness",
            "team availability",
        ],
        preferred_sources=["jira", "confluence", "release_notes", "bug_history"],
        retrieval_hints=["test matrix", "regression history", "qa capacity"],
    ),
    "design": TeamContextPolicy(
        team="design",
        focus_areas=["user flow", "edge cases", "consistency", "design bandwidth"],
        preferred_sources=["confluence", "drive", "roadmap"],
        retrieval_hints=["user flow", "edge cases", "design readiness"],
    ),
    "support": TeamContextPolicy(
        team="support",
        focus_areas=[
            "customer confusion risk",
            "ticket impact",
            "docs and escalation readiness",
            "support capacity",
        ],
        preferred_sources=["jira", "confluence", "support_tickets", "help_center"],
        retrieval_hints=["ticket trends", "known pain points", "support staffing"],
    ),
    "gtm": TeamContextPolicy(
        team="gtm",
        focus_areas=["launch timing", "messaging", "segmentation", "go-to-market bandwidth"],
        preferred_sources=["confluence", "drive", "roadmap"],
        retrieval_hints=["launch plan", "messaging dependencies", "campaign readiness"],
    ),
    "security_privacy": TeamContextPolicy(
        team="security_privacy",
        focus_areas=["data exposure", "permissions", "compliance", "review capacity"],
        preferred_sources=["confluence", "jira", "privacy_docs"],
        retrieval_hints=["data classification", "consent language", "security review dependencies"],
    ),
    "tpm": TeamContextPolicy(
        team="tpm",
        focus_areas=[
            "sequencing",
            "cross-team risk",
            "ownership map",
            "timeline realism",
            "capacity risk",
        ],
        preferred_sources=["jira", "confluence", "roadmap", "release_calendar"],
        retrieval_hints=["critical path", "dependency ordering", "owner assignment", "timeline risk"],
    ),
}


def _default_policy_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "team_context_policies.json"


def load_team_policies(policy_path: Path | None = None) -> dict[str, TeamContextPolicy]:
    policies = dict(DEFAULT_TEAM_POLICIES)

    configured_path = policy_path
    if configured_path is None:
        env_path = os.getenv("PREFLIGHT_TEAM_POLICY_PATH")
        configured_path = Path(env_path) if env_path else _default_policy_path()

    if not configured_path.exists():
        return policies

    payload = json.loads(configured_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return policies

    for team, values in payload.items():
        if not isinstance(values, dict):
            continue
        policy = TeamContextPolicy(
            team=team,
            focus_areas=list(values.get("focus_areas", [])),
            preferred_sources=list(values.get("preferred_sources", [])),
            retrieval_hints=list(values.get("retrieval_hints", [])),
        )
        policies[team] = policy

    return policies
