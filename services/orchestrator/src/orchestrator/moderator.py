from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

from preflight_schemas import AgentReview, InitiativeBrief, ModeratorSummary, ReadinessStatus

from .llm_client import LLMClientError, OpenAIChatClient


OWNER_BY_TEAM = {
    "engineering": "Engineering Lead",
    "qa": "QA Lead",
    "design": "Design Lead",
    "support": "Support Lead",
    "gtm": "GTM Lead",
    "security": "Security Lead",
    "privacy": "Privacy Lead",
    "security_privacy": "Security/Privacy Lead",
    "tpm": "TPM",
}


@dataclass
class ModeratorConfig:
    max_blockers: int = 5
    max_dependencies: int = 5
    max_questions: int = 8
    max_owners: int = 6
    max_agenda_items: int = 6


class Moderator(Protocol):
    def summarize(
        self,
        brief: InitiativeBrief,
        team_reviews: list[AgentReview],
        warnings: list[str] | None = None,
    ) -> ModeratorSummary:
        """Produce final moderator synthesis from team reviews."""


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _coerce_readiness(value: str) -> ReadinessStatus:
    lowered = value.strip().lower()
    if lowered == "red":
        return ReadinessStatus.RED
    if lowered == "green":
        return ReadinessStatus.GREEN
    return ReadinessStatus.YELLOW


def _normalize_list(value: object, max_items: int) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return _dedupe_preserve_order(normalized)[:max_items]


def _extract_json_object(raw: str) -> dict:
    raw = raw.strip()
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        return json.loads(raw[start : end + 1])

    raise ValueError("No JSON object found in moderator output")


def _build_base_summary(
    team_reviews: list[AgentReview],
    warnings: list[str] | None,
) -> ModeratorSummary:
    blockers = _dedupe_preserve_order(
        [
            blocker
            for review in team_reviews
            for concern in review.concerns
            for blocker in concern.blockers
        ]
    )
    questions_to_resolve = _dedupe_preserve_order(
        [
            question
            for review in team_reviews
            for concern in review.concerns
            for question in concern.questions
        ]
    )

    suggested_owners = _dedupe_preserve_order(
        [
            OWNER_BY_TEAM.get(review.team.lower(), "TPM")
            for review in team_reviews
            if review.concerns
        ]
    )

    readiness_values = {review.readiness for review in team_reviews}
    if ReadinessStatus.RED in readiness_values:
        overall_readiness = ReadinessStatus.RED
    elif ReadinessStatus.YELLOW in readiness_values:
        overall_readiness = ReadinessStatus.YELLOW
    else:
        overall_readiness = ReadinessStatus.GREEN

    kickoff_agenda: list[str] = [
        "Confirm user problem and success metric",
        "Clarify cross-team ownership and dependencies",
    ]
    if blockers:
        kickoff_agenda.append("Resolve top blockers and assign owners")
    if questions_to_resolve:
        kickoff_agenda.append("Answer unresolved implementation and release questions")

    return ModeratorSummary(
        overall_readiness=overall_readiness,
        blockers=blockers,
        dependencies=[],
        questions_to_resolve=questions_to_resolve,
        suggested_owners=suggested_owners,
        kickoff_agenda=_dedupe_preserve_order(kickoff_agenda),
        warnings=_dedupe_preserve_order(warnings or []),
    )


class DeterministicModerator:
    def __init__(self, config: ModeratorConfig | None = None) -> None:
        self.config = config or ModeratorConfig()

    def summarize(
        self,
        brief: InitiativeBrief,
        team_reviews: list[AgentReview],
        warnings: list[str] | None = None,
    ) -> ModeratorSummary:
        base = _build_base_summary(team_reviews, warnings)
        base.blockers = base.blockers[: self.config.max_blockers]
        base.dependencies = base.dependencies[: self.config.max_dependencies]
        base.questions_to_resolve = base.questions_to_resolve[: self.config.max_questions]
        base.suggested_owners = base.suggested_owners[: self.config.max_owners]
        base.kickoff_agenda = base.kickoff_agenda[: self.config.max_agenda_items]
        return base


class LLMModerator:
    def __init__(self, llm_client: OpenAIChatClient, config: ModeratorConfig | None = None) -> None:
        self.llm_client = llm_client
        self.config = config or ModeratorConfig()

    def _build_user_prompt(self, brief: InitiativeBrief, team_reviews: list[AgentReview]) -> str:
        reviews_json = json.dumps([review.model_dump() for review in team_reviews], ensure_ascii=True)
        return (
            "You are the Moderator Agent for PreFlight. Synthesize team reviews into a concise kickoff-readiness summary.\n"
            f"Initiative:\n"
            f"- title: {brief.title}\n"
            f"- problem_statement: {brief.problem_statement}\n"
            f"- proposed_solution: {brief.proposed_solution}\n"
            f"- target_timeline: {brief.target_timeline}\n"
            f"- affected_teams: {', '.join(brief.affected_teams) or 'not specified'}\n"
            f"- success_metric: {brief.success_metric}\n"
            f"- known_constraints: {', '.join(brief.known_constraints) or 'none'}\n\n"
            f"Team reviews JSON:\n{reviews_json}\n\n"
            "Return ONLY JSON with schema:\n"
            "{\n"
            "  \"overall_readiness\": \"green|yellow|red\",\n"
            "  \"blockers\": [\"string\"],\n"
            "  \"dependencies\": [\"string\"],\n"
            "  \"questions_to_resolve\": [\"string\"],\n"
            "  \"suggested_owners\": [\"string\"],\n"
            "  \"kickoff_agenda\": [\"string\"]\n"
            "}\n"
            "Prioritize high-signal cross-team issues and keep each list concise."
        )

    def summarize(
        self,
        brief: InitiativeBrief,
        team_reviews: list[AgentReview],
        warnings: list[str] | None = None,
    ) -> ModeratorSummary:
        base = _build_base_summary(team_reviews, warnings)
        system_prompt = (
            "You are a strict JSON-only synthesis assistant. "
            "Do not invent data not grounded in provided team reviews."
        )

        try:
            response = self.llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=self._build_user_prompt(brief, team_reviews),
            )
            payload = _extract_json_object(response.content)
        except (LLMClientError, ValueError, json.JSONDecodeError) as exc:
            base.warnings.append(f"moderator synthesis fallback used ({exc})")
            return DeterministicModerator(config=self.config).summarize(brief, team_reviews, base.warnings)

        try:
            synthesized = ModeratorSummary(
                overall_readiness=_coerce_readiness(str(payload.get("overall_readiness", base.overall_readiness.value))),
                blockers=_normalize_list(payload.get("blockers", []), self.config.max_blockers) or base.blockers[: self.config.max_blockers],
                dependencies=_normalize_list(payload.get("dependencies", []), self.config.max_dependencies),
                questions_to_resolve=_normalize_list(payload.get("questions_to_resolve", []), self.config.max_questions) or base.questions_to_resolve[: self.config.max_questions],
                suggested_owners=_normalize_list(payload.get("suggested_owners", []), self.config.max_owners) or base.suggested_owners[: self.config.max_owners],
                kickoff_agenda=_normalize_list(payload.get("kickoff_agenda", []), self.config.max_agenda_items) or base.kickoff_agenda[: self.config.max_agenda_items],
                warnings=_dedupe_preserve_order(base.warnings),
            )
            return synthesized
        except Exception as exc:  # noqa: BLE001
            base.warnings.append(f"moderator synthesis parse fallback used ({exc})")
            return DeterministicModerator(config=self.config).summarize(brief, team_reviews, base.warnings)


def build_default_moderator() -> Moderator:
    mode = os.getenv("PREFLIGHT_MODERATOR_MODE", "auto").strip().lower()
    config = ModeratorConfig(
        max_blockers=int(os.getenv("PREFLIGHT_MODERATOR_MAX_BLOCKERS", "5")),
        max_dependencies=int(os.getenv("PREFLIGHT_MODERATOR_MAX_DEPENDENCIES", "5")),
        max_questions=int(os.getenv("PREFLIGHT_MODERATOR_MAX_QUESTIONS", "8")),
        max_owners=int(os.getenv("PREFLIGHT_MODERATOR_MAX_OWNERS", "6")),
        max_agenda_items=int(os.getenv("PREFLIGHT_MODERATOR_MAX_AGENDA_ITEMS", "6")),
    )

    if mode in {"auto", "llm"}:
        client = OpenAIChatClient.from_env()
        if client is not None:
            return LLMModerator(llm_client=client, config=config)
        if mode == "llm":
            return DeterministicModerator(config=config)

    return DeterministicModerator(config=config)
