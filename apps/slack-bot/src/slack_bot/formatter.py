from __future__ import annotations

from preflight_schemas import ReviewRun


def _title_case(team: str) -> str:
    if team.lower() == "qa":
        return "QA"
    if team.lower() == "gtm":
        return "GTM"
    if team.lower() == "tpm":
        return "TPM"
    return team.title()


def format_thread_message(run: ReviewRun) -> str:
    lines: list[str] = []
    summary = run.moderator_summary

    lines.append(f"PreFlight Review: {run.initiative_title}")
    lines.append(f"Overall readiness: {summary.overall_readiness.value.upper()}")

    if summary.warnings:
        lines.append("Warnings:")
        for warning in summary.warnings:
            lines.append(f"- {warning}")

    if summary.blockers:
        lines.append("Top blockers:")
        for blocker in summary.blockers:
            lines.append(f"- {blocker}")

    if summary.questions_to_resolve:
        lines.append("Questions to resolve:")
        for question in summary.questions_to_resolve:
            lines.append(f"- {question}")

    if summary.suggested_owners:
        lines.append("Suggested owners:")
        for owner in summary.suggested_owners:
            lines.append(f"- {owner}")

    lines.append("Team perspectives:")
    for review in run.team_reviews:
        lines.append(f"- {_title_case(review.team)}: {review.readiness.value.upper()}")
        for concern in review.concerns:
            lines.append(
                f"  - Concern: {concern.statement} "
                f"[{concern.evidence_status.value}; conf={concern.confidence:.2f}]"
            )

    if summary.kickoff_agenda:
        lines.append("Suggested kickoff agenda:")
        for idx, agenda_item in enumerate(summary.kickoff_agenda, start=1):
            lines.append(f"{idx}. {agenda_item}")

    return "\n".join(lines)
