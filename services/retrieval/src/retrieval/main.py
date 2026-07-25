from __future__ import annotations

import json
import re
from pathlib import Path

from preflight_schemas import RetrievedSnippet, SourceDocument


def _default_index_path() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "index" / "seed_documents.jsonl"


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _is_doc_visible_to_team(team: str, doc: SourceDocument) -> bool:
    if not doc.team_scope:
        return True

    normalized_scope = {scope.lower() for scope in doc.team_scope}
    return team.lower() in normalized_scope or "all" in normalized_scope


def _build_excerpt(body: str, token_hint: str | None, max_chars: int = 220) -> str:
    if not token_hint:
        return body[:max_chars].strip()

    lowered = body.lower()
    index = lowered.find(token_hint)
    if index < 0:
        return body[:max_chars].strip()

    start = max(0, index - 50)
    end = min(len(body), index + 170)
    trimmed_start = start > 0
    trimmed_end = end < len(body)

    if trimmed_start:
        next_space = body.find(" ", start)
        if 0 <= next_space < index:
            start = next_space + 1
    if trimmed_end:
        previous_space = body.rfind(" ", start, end)
        if previous_space > index:
            end = previous_space

    excerpt = body[start:end].strip()
    if trimmed_start:
        excerpt = f"... {excerpt}"
    if trimmed_end:
        excerpt = f"{excerpt} ..."
    return excerpt


def retrieve_context(
    team: str,
    query: str,
    max_results: int = 5,
    index_path: Path | None = None,
) -> list[RetrievedSnippet]:
    active_index_path = index_path or _default_index_path()
    if not active_index_path.exists():
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    snippets: list[RetrievedSnippet] = []
    with active_index_path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            raw = line.strip()
            if not raw:
                continue

            document = SourceDocument.model_validate(json.loads(raw))
            if not _is_doc_visible_to_team(team, document):
                continue

            doc_tokens = _tokenize(" ".join([document.title, document.body, " ".join(document.tags)]))
            overlap = query_tokens.intersection(doc_tokens)
            if not overlap:
                continue

            score = len(overlap) / max(len(query_tokens), 1)
            hint = next(iter(overlap), None)
            snippets.append(
                RetrievedSnippet(
                    team=team,
                    source_id=document.source_id,
                    source_type=document.source_type,
                    title=document.title,
                    excerpt=_build_excerpt(document.body, hint),
                    score=round(score, 4),
                )
            )

    snippets.sort(key=lambda snippet: snippet.score, reverse=True)
    return snippets[:max_results]
