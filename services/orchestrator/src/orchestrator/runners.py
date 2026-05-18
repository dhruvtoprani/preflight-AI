from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from pydantic import ValidationError

from preflight_schemas import (
    AgentReview,
    Concern,
    EvidenceReference,
    EvidenceStatus,
    InitiativeBrief,
    ReadinessStatus,
)

from retrieval.main import retrieve_context

from .llm_client import LLMClientError, OpenAIChatClient
from .prompting import SYSTEM_PROMPT, PromptRepository, build_team_user_prompt
from .team_policies import TeamContextPolicy, load_team_policies


SUPPORTED_TEAMS = [
    "engineering",
    "qa",
    "design",
    "support",
    "gtm",
    "security_privacy",
    "tpm",
]

TEAM_ALIASES = {
    "security": "security_privacy",
    "privacy": "security_privacy",
    "security/privacy": "security_privacy",
}


@dataclass
class RunnerResult:
    team_reviews: list[AgentReview]
    warnings: list[str]


class AgentRunner(Protocol):
    def run(self, brief: InitiativeBrief) -> RunnerResult:
        """Return role-scoped team reviews and execution warnings."""


def _engineering_review(brief: InitiativeBrief) -> AgentReview:
    eng_concern = Concern(
        team="engineering",
        statement="API ownership is not yet explicit for mobile notification workflows.",
        confidence=0.76,
        evidence_status=EvidenceStatus.INFERRED,
        evidence=[
            EvidenceReference(
                source_type="roadmap",
                source_id="Q3-Mobile-Roadmap",
                excerpt="Notification API contract milestone listed without owner.",
            )
        ],
        blockers=["Assign API owner"],
        questions=["Which team owns API contract and rollout sequencing?"],
    )
    return AgentReview(
        team="engineering",
        readiness=ReadinessStatus.YELLOW,
        concerns=[eng_concern],
    )


def _qa_review(brief: InitiativeBrief) -> AgentReview:
    qa_concern = Concern(
        team="qa",
        statement="Regression risk exists across notification settings and onboarding flows.",
        confidence=0.82,
        evidence_status=EvidenceStatus.EVIDENCE_BACKED,
        evidence=[
            EvidenceReference(
                source_type="release_notes",
                source_id="Q2-Release-Checklist",
                excerpt="Two prior regressions linked to notification preference migration.",
            )
        ],
        blockers=["Estimate test matrix"],
        questions=["Do we have dedicated QA capacity for multi-pet edge cases?"],
    )
    return AgentReview(
        team="qa",
        readiness=ReadinessStatus.RED,
        concerns=[qa_concern],
    )


def _deterministic_generic_review(
    team: str,
    statement: str,
    question: str,
    blocker: str | None = None,
) -> AgentReview:
    blockers = [blocker] if blocker else []
    concern = Concern(
        team=team,
        statement=statement,
        confidence=0.64,
        evidence_status=EvidenceStatus.INFERRED,
        evidence=[],
        blockers=blockers,
        questions=[question],
    )
    return AgentReview(team=team, readiness=ReadinessStatus.YELLOW, concerns=[concern])


def _design_review(brief: InitiativeBrief) -> AgentReview:
    return _deterministic_generic_review(
        team="design",
        statement="Primary user flow and edge-case states are not yet fully defined for kickoff.",
        question="What design states and copy variants are required for beta scope?",
    )


def _support_review(brief: InitiativeBrief) -> AgentReview:
    return _deterministic_generic_review(
        team="support",
        statement="Support readiness is unclear for expected user confusion and escalation handling.",
        question="Who owns help-center updates and escalation playbooks before launch?",
        blocker="Assign support-readiness owner",
    )


def _gtm_review(brief: InitiativeBrief) -> AgentReview:
    return _deterministic_generic_review(
        team="gtm",
        statement="GTM timeline and launch messaging dependencies are not fully aligned.",
        question="Which launch milestones and messaging approvals gate release readiness?",
    )


def _security_privacy_review(brief: InitiativeBrief) -> AgentReview:
    return _deterministic_generic_review(
        team="security_privacy",
        statement="Security/privacy review scope remains undefined for this initiative.",
        question="What data-access and compliance checks must clear before kickoff approval?",
        blocker="Scope security/privacy review",
    )


def _tpm_review(brief: InitiativeBrief) -> AgentReview:
    return _deterministic_generic_review(
        team="tpm",
        statement="Cross-team sequencing and ownership map are incomplete for kickoff quality.",
        question="Can we confirm owners, milestones, and dependency order for kickoff?",
        blocker="Finalize owner/dependency map",
    )


class DeterministicRunner:
    """MVP deterministic runner used until live agent orchestration is wired."""

    def __init__(self, timeout_teams: list[str] | None = None) -> None:
        self.timeout_teams = {team.lower() for team in (timeout_teams or [])}

    def run(self, brief: InitiativeBrief) -> RunnerResult:
        team_functions: dict[str, Callable[[InitiativeBrief], AgentReview]] = {
            "engineering": _engineering_review,
            "qa": _qa_review,
            "design": _design_review,
            "support": _support_review,
            "gtm": _gtm_review,
            "security_privacy": _security_privacy_review,
            "tpm": _tpm_review,
        }

        selected_teams = _select_teams(brief)

        team_reviews: list[AgentReview] = []
        warnings: list[str] = []

        for team in selected_teams:
            build_review = team_functions.get(team)
            if build_review is None:
                warnings.append(f"{team} deterministic review unavailable; fallback used")
                team_reviews.append(_build_fallback_review(team, "deterministic review unavailable"))
                continue

            try:
                if team in self.timeout_teams:
                    raise TimeoutError(f"{team} agent timed out")
                team_reviews.append(build_review(brief))
            except TimeoutError:
                warnings.append(
                    f"{team} agent timed out; review contains partial results"
                )

        return RunnerResult(team_reviews=team_reviews, warnings=warnings)


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

    raise ValueError("No JSON object found in model output")


def _normalize_team(team: str) -> str:
    cleaned = team.strip().lower()
    cleaned = TEAM_ALIASES.get(cleaned, cleaned)
    return cleaned


def _select_teams(brief: InitiativeBrief) -> list[str]:
    if not brief.affected_teams:
        return list(SUPPORTED_TEAMS)

    selected: list[str] = []
    for team in brief.affected_teams:
        normalized = _normalize_team(team)
        if normalized in SUPPORTED_TEAMS and normalized not in selected:
            selected.append(normalized)

    return selected or list(SUPPORTED_TEAMS)


def _coerce_readiness(value: str) -> ReadinessStatus:
    lowered = value.strip().lower()
    if lowered == "red":
        return ReadinessStatus.RED
    if lowered == "green":
        return ReadinessStatus.GREEN
    return ReadinessStatus.YELLOW


def _build_fallback_review(team: str, reason: str) -> AgentReview:
    return AgentReview(
        team=team,
        readiness=ReadinessStatus.YELLOW,
        concerns=[
            Concern(
                team=team,
                statement="Automated analysis for this team failed; manual review required.",
                confidence=0.2,
                evidence_status=EvidenceStatus.NEEDS_CONFIRMATION,
                evidence=[],
                blockers=[],
                questions=[f"Can {team} provide explicit blockers and dependencies manually?"],
            )
        ],
    )


def _build_concerns(
    team: str,
    raw_concerns: list[dict],
    warnings: list[str],
) -> list[Concern]:
    concerns: list[Concern] = []

    for idx, raw_concern in enumerate(raw_concerns):
        if not isinstance(raw_concern, dict):
            continue

        evidence_payload = raw_concern.get("evidence", [])
        if not isinstance(evidence_payload, list):
            evidence_payload = []

        concern_payload = {
            "team": team,
            "statement": str(raw_concern.get("statement", "Potential risk requires confirmation.")),
            "confidence": float(raw_concern.get("confidence", 0.5)),
            "evidence_status": str(raw_concern.get("evidence_status", "needs confirmation")),
            "evidence": evidence_payload,
            "blockers": list(raw_concern.get("blockers", [])),
            "questions": list(raw_concern.get("questions", [])),
        }

        try:
            concerns.append(Concern.model_validate(concern_payload))
            continue
        except ValidationError as exc:
            if (
                concern_payload["evidence_status"]
                == EvidenceStatus.EVIDENCE_BACKED.value
                and not concern_payload["evidence"]
            ):
                concern_payload["evidence_status"] = EvidenceStatus.NEEDS_CONFIRMATION.value
                concerns.append(Concern.model_validate(concern_payload))
                warnings.append(
                    f"{team} concern[{idx}] downgraded to needs confirmation due to missing evidence"
                )
                continue
            warnings.append(f"{team} concern[{idx}] dropped due to validation error: {exc.errors()}")

    if concerns:
        return concerns

    return [
        Concern(
            team=team,
            statement="Insufficient validated concerns returned; manual confirmation required.",
            confidence=0.2,
            evidence_status=EvidenceStatus.NEEDS_CONFIRMATION,
            evidence=[],
            blockers=[],
            questions=["Can this team provide a clearer risk statement with evidence?"],
        )
    ]


class LLMTeamRunner:
    def __init__(
        self,
        llm_client: OpenAIChatClient,
        timeout_teams: list[str] | None = None,
        prompt_repository: PromptRepository | None = None,
        team_policies: dict[str, TeamContextPolicy] | None = None,
        index_path: Path | None = None,
        max_workers: int | None = None,
        review_timeout_seconds: float | None = None,
        llm_retries: int | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.timeout_teams = {_normalize_team(team) for team in (timeout_teams or [])}
        self.prompt_repository = prompt_repository or PromptRepository()
        self.team_policies = team_policies or load_team_policies()
        self.index_path = index_path
        self.max_workers = max_workers or int(os.getenv("PREFLIGHT_MAX_PARALLEL_AGENTS", "4"))
        self.review_timeout_seconds = review_timeout_seconds or float(
            os.getenv("PREFLIGHT_REVIEW_TIMEOUT_SECONDS", "50")
        )
        self.llm_retries = llm_retries if llm_retries is not None else int(
            os.getenv("PREFLIGHT_LLM_RETRIES", "1")
        )

    def _run_team_review(self, team: str, brief: InitiativeBrief) -> tuple[AgentReview, list[str]]:
        warnings: list[str] = []

        policy = self.team_policies.get(team)
        if policy is None:
            policy = TeamContextPolicy(
                team=team,
                focus_areas=["readiness", "blockers", "questions", "availability"],
                preferred_sources=[],
                retrieval_hints=[],
            )

        retrieval_query = " ".join(
            [brief.title, brief.problem_statement, brief.proposed_solution, " ".join(policy.retrieval_hints)]
        )
        snippets = retrieve_context(
            team=team,
            query=retrieval_query,
            max_results=5,
            index_path=self.index_path,
        )

        team_template = self.prompt_repository.load_team_template(team)
        user_prompt = build_team_user_prompt(
            team=team,
            brief=brief,
            policy=policy,
            team_template=team_template,
            snippets=snippets,
        )

        last_exception: Exception | None = None
        payload: dict | None = None
        attempts = max(self.llm_retries + 1, 1)
        for attempt in range(1, attempts + 1):
            try:
                response = self.llm_client.complete(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
                payload = _extract_json_object(response.content)
                break
            except (LLMClientError, ValueError, json.JSONDecodeError) as exc:
                last_exception = exc
                if attempt < attempts:
                    warnings.append(f"{team} model call retry {attempt}/{attempts - 1} after error: {exc}")

        if payload is None:
            reason = str(last_exception or "unknown model error")
            warnings.append(f"{team} model call failed; fallback concern used ({reason})")
            return _build_fallback_review(team, reason), warnings

        readiness = _coerce_readiness(str(payload.get("readiness", "yellow")))
        raw_concerns = payload.get("concerns", [])
        if not isinstance(raw_concerns, list):
            raw_concerns = []

        concerns = _build_concerns(team=team, raw_concerns=raw_concerns, warnings=warnings)

        return (
            AgentReview(
                team=team,
                readiness=readiness,
                concerns=concerns,
            ),
            warnings,
        )

    def run(self, brief: InitiativeBrief) -> RunnerResult:
        selected_teams = _select_teams(brief)
        warnings: list[str] = []
        review_by_team: dict[str, AgentReview] = {}

        immediate_teams: list[str] = []
        for team in selected_teams:
            if team in self.timeout_teams:
                warnings.append(f"{team} agent timed out; review contains partial results")
                review_by_team[team] = _build_fallback_review(team, "timeout override")
            else:
                immediate_teams.append(team)

        if immediate_teams:
            worker_count = max(1, min(self.max_workers, len(immediate_teams)))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_to_team = {
                    executor.submit(self._run_team_review, team, brief): team
                    for team in immediate_teams
                }

                done, not_done = wait(
                    future_to_team.keys(),
                    timeout=self.review_timeout_seconds,
                )

                for future in done:
                    team = future_to_team[future]
                    try:
                        review, team_warnings = future.result()
                        review_by_team[team] = review
                        warnings.extend(team_warnings)
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"{team} review failed; fallback used ({exc})")
                        review_by_team[team] = _build_fallback_review(team, str(exc))

                for future in not_done:
                    team = future_to_team[future]
                    future.cancel()
                    warnings.append(
                        f"{team} review timed out after {self.review_timeout_seconds:.1f}s; fallback used"
                    )
                    review_by_team[team] = _build_fallback_review(team, "review timeout")

        ordered_reviews: list[AgentReview] = [
            review_by_team[team] for team in selected_teams if team in review_by_team
        ]
        return RunnerResult(team_reviews=ordered_reviews, warnings=warnings)


def build_default_runner(timeout_teams: list[str] | None = None) -> AgentRunner:
    mode = os.getenv("PREFLIGHT_RUNNER_MODE", "auto").strip().lower()
    timeout_teams = timeout_teams or []

    if mode in {"auto", "llm"}:
        llm_client = OpenAIChatClient.from_env()
        if llm_client is not None:
            index_path_env = os.getenv("PREFLIGHT_INDEX_PATH")
            index_path = Path(index_path_env) if index_path_env else None
            return LLMTeamRunner(
                llm_client=llm_client,
                timeout_teams=timeout_teams,
                index_path=index_path,
            )
        if mode == "llm":
            # Explicitly requested LLM mode but key is missing.
            return DeterministicRunner(timeout_teams=timeout_teams)

    return DeterministicRunner(timeout_teams=timeout_teams)
