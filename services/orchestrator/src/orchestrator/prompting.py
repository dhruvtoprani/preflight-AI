from __future__ import annotations

import os
from pathlib import Path

from preflight_schemas import InitiativeBrief, RetrievedSnippet

from .team_policies import TeamContextPolicy


SYSTEM_PROMPT = (
    "You are a role-specific stakeholder review agent for initiative readiness. "
    "Be concrete, risk-aware, and honest about uncertainty. "
    "Return only valid JSON matching the requested schema."
)


def _default_template_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "packages" / "agent-prompts" / "templates"


class PromptRepository:
    def __init__(self, template_dir: Path | None = None) -> None:
        env_dir = os.getenv("PREFLIGHT_PROMPT_TEMPLATE_DIR")
        self.template_dir = template_dir or (Path(env_dir) if env_dir else _default_template_dir())

    def load_team_template(self, team: str) -> str:
        candidates = [
            self.template_dir / f"{team}.md",
            self.template_dir / "general.md",
        ]

        for file_path in candidates:
            if file_path.exists():
                return file_path.read_text(encoding="utf-8").strip()

        return "Focus on blockers, dependencies, unanswered questions, and team availability risks."


def build_team_user_prompt(
    team: str,
    brief: InitiativeBrief,
    policy: TeamContextPolicy,
    team_template: str,
    snippets: list[RetrievedSnippet],
) -> str:
    snippet_lines: list[str] = []
    for snippet in snippets:
        snippet_lines.append(
            "- "
            f"[{snippet.source_type}:{snippet.source_id}] "
            f"{snippet.title} | score={snippet.score} | excerpt={snippet.excerpt}"
        )

    snippets_block = "\n".join(snippet_lines) if snippet_lines else "- No matching snippets found"

    return (
        f"TEAM: {team}\n"
        f"TEAM TEMPLATE:\n{team_template}\n\n"
        f"ALLOWED DOCUMENTATION SOURCES: {', '.join(policy.preferred_sources) or 'none specified'}\n"
        f"FOCUS AREAS: {', '.join(policy.focus_areas) or 'none specified'}\n"
        f"RETRIEVAL HINTS: {', '.join(policy.retrieval_hints) or 'none specified'}\n\n"
        f"INITIATIVE BRIEF:\n"
        f"- title: {brief.title}\n"
        f"- problem_statement: {brief.problem_statement}\n"
        f"- proposed_solution: {brief.proposed_solution}\n"
        f"- target_timeline: {brief.target_timeline}\n"
        f"- affected_teams: {', '.join(brief.affected_teams) or 'not specified'}\n"
        f"- success_metric: {brief.success_metric}\n"
        f"- known_constraints: {', '.join(brief.known_constraints) or 'none'}\n\n"
        f"TEAM-SCOPED CONTEXT SNIPPETS:\n{snippets_block}\n\n"
        "TASK:\n"
        "1) Analyze this initiative from your team lens.\n"
        "2) Evaluate readiness, blockers, dependencies, open questions, and team availability risks.\n"
        "3) If evidence is weak or missing, mark concerns as needs confirmation.\n"
        "4) Do not invent unavailable documents; only reference provided snippets.\n\n"
        "OUTPUT JSON ONLY using this schema:\n"
        "{\n"
        "  \"readiness\": \"green|yellow|red\",\n"
        "  \"concerns\": [\n"
        "    {\n"
        "      \"statement\": \"string\",\n"
        "      \"confidence\": 0.0,\n"
        "      \"evidence_status\": \"evidence-backed|inferred|needs confirmation\",\n"
        "      \"blockers\": [\"string\"],\n"
        "      \"questions\": [\"string\"],\n"
        "      \"evidence\": [\n"
        "        {\"source_type\": \"string\", \"source_id\": \"string\", \"excerpt\": \"string\"}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Limit concerns to 2-4 high-signal items."
    )
