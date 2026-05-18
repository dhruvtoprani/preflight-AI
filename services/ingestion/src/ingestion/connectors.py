from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from preflight_schemas import SourceDocument


class ConnectorError(RuntimeError):
    pass


@dataclass
class ConnectorFetchResult:
    documents: list[SourceDocument]
    next_cursor: str | None


class SourceConnector(Protocol):
    name: str

    def fetch_updates(self, since_cursor: str | None = None) -> ConnectorFetchResult:
        """Fetch normalized source documents newer than checkpoint."""


def _basic_auth_header(email: str, api_token: str) -> str:
    raw = f"{email}:{api_token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("utf-8")


def _clean_base_url(base_url: str) -> str:
    parsed = urlparse(base_url.strip())
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _http_get_json(url: str, headers: dict[str, str], timeout_seconds: int = 30) -> dict:
    request = Request(url=url, method="GET", headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_extract_text(item) for item in value)
    if isinstance(value, dict):
        parts: list[str] = []
        for key in ("text", "value", "content", "body", "storage"):
            if key in value:
                parts.append(_extract_text(value[key]))
        if parts:
            return " ".join(parts)
        return " ".join(_extract_text(item) for item in value.values())
    return ""


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def _normalize_scope(values: list[str]) -> list[str]:
    normalized = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip().lower().replace("-", "_").replace("/", "_")
        if not cleaned:
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized


def _scope_from_labels(labels: list[str]) -> list[str]:
    scopes: list[str] = []
    for label in labels:
        lowered = label.lower().strip()
        if lowered.startswith("team:"):
            scopes.append(lowered.split(":", 1)[1])
        elif lowered.startswith("scope:"):
            scopes.append(lowered.split(":", 1)[1])
    return _normalize_scope(scopes)


def _scope_from_text(text: str) -> list[str]:
    matches = re.findall(r"(?:team|scope):([a-zA-Z0-9_\-/]+)", text)
    return _normalize_scope(matches)


def _parse_iso_timestamp(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value}")


def _is_newer(updated_at: str, since_cursor: str | None) -> bool:
    if not since_cursor:
        return True
    try:
        return _parse_iso_timestamp(updated_at) >= _parse_iso_timestamp(since_cursor)
    except ValueError:
        return True


class SeedDumpConnector:
    """Connector for local exported dumps (MVP)."""

    name = "seed_dump"

    def __init__(self, source_dir, http_get_json: Callable | None = None) -> None:
        self.source_dir = source_dir

    def fetch_updates(self, since_cursor: str | None = None) -> ConnectorFetchResult:
        documents: list[SourceDocument] = []
        for file_path in sorted(self.source_dir.rglob("*.json")):
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload = [payload]
            if not isinstance(payload, list):
                continue
            for raw_document in payload:
                documents.append(SourceDocument.model_validate(raw_document))
        return ConnectorFetchResult(documents=documents, next_cursor=since_cursor)


class JiraConnector:
    name = "jira"

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        jql_filter: str = "",
        page_size: int = 50,
        timeout_seconds: int = 30,
        http_get_json: Callable[[str, dict[str, str], int], dict] = _http_get_json,
    ) -> None:
        self.base_url = _clean_base_url(base_url)
        self.email = email
        self.api_token = api_token
        self.jql_filter = jql_filter.strip()
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.http_get_json = http_get_json

    @classmethod
    def from_env(cls) -> "JiraConnector | None":
        base_url = os.getenv("JIRA_BASE_URL")
        email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")
        if not (base_url and email and api_token):
            return None
        return cls(
            base_url=base_url,
            email=email,
            api_token=api_token,
            jql_filter=os.getenv("JIRA_JQL_FILTER", ""),
            page_size=int(os.getenv("JIRA_PAGE_SIZE", "50")),
            timeout_seconds=int(os.getenv("JIRA_TIMEOUT_SECONDS", "30")),
        )

    def _build_jql(self, since_cursor: str | None) -> str:
        clauses: list[str] = []
        if self.jql_filter:
            clauses.append(f"({self.jql_filter})")
        if since_cursor:
            clauses.append(f'updated >= "{since_cursor}"')
        base = " AND ".join(clauses)
        if base:
            return f"{base} ORDER BY updated ASC"
        return "ORDER BY updated ASC"

    def fetch_updates(self, since_cursor: str | None = None) -> ConnectorFetchResult:
        headers = {
            "Authorization": _basic_auth_header(self.email, self.api_token),
            "Accept": "application/json",
        }
        start_at = 0
        total = None
        documents: list[SourceDocument] = []
        latest_cursor = since_cursor

        while total is None or start_at < total:
            params = {
                "jql": self._build_jql(since_cursor),
                "startAt": start_at,
                "maxResults": self.page_size,
                "fields": "summary,description,updated,labels",
            }
            url = f"{self.base_url}/rest/api/3/search?{urlencode(params)}"
            payload = self.http_get_json(url, headers, self.timeout_seconds)
            issues = payload.get("issues", [])
            total = int(payload.get("total", 0))

            for issue in issues:
                issue_key = str(issue.get("key", ""))
                fields = issue.get("fields", {}) or {}
                updated_at = str(fields.get("updated", ""))
                if updated_at and not _is_newer(updated_at, since_cursor):
                    continue

                description_text = _extract_text(fields.get("description"))
                labels = [str(label) for label in fields.get("labels", [])]
                scope = _scope_from_labels(labels) or ["all"]
                title = str(fields.get("summary", issue_key or "Jira issue"))
                body = description_text or title
                document = SourceDocument(
                    source_id=issue_key,
                    source_type="jira",
                    title=title,
                    body=body,
                    team_scope=scope,
                    tags=labels,
                )
                documents.append(document)

                if updated_at:
                    if latest_cursor is None or _is_newer(updated_at, latest_cursor):
                        latest_cursor = updated_at

            start_at += self.page_size
            if not issues:
                break

        return ConnectorFetchResult(documents=documents, next_cursor=latest_cursor)


class ConfluenceConnector:
    name = "confluence"

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        page_size: int = 50,
        timeout_seconds: int = 30,
        http_get_json: Callable[[str, dict[str, str], int], dict] = _http_get_json,
    ) -> None:
        self.base_url = _clean_base_url(base_url)
        self.email = email
        self.api_token = api_token
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.http_get_json = http_get_json

    @classmethod
    def from_env(cls) -> "ConfluenceConnector | None":
        base_url = os.getenv("CONFLUENCE_BASE_URL")
        email = os.getenv("CONFLUENCE_EMAIL")
        api_token = os.getenv("CONFLUENCE_API_TOKEN")
        if not (base_url and email and api_token):
            return None
        return cls(
            base_url=base_url,
            email=email,
            api_token=api_token,
            page_size=int(os.getenv("CONFLUENCE_PAGE_SIZE", "50")),
            timeout_seconds=int(os.getenv("CONFLUENCE_TIMEOUT_SECONDS", "30")),
        )

    def fetch_updates(self, since_cursor: str | None = None) -> ConnectorFetchResult:
        headers = {
            "Authorization": _basic_auth_header(self.email, self.api_token),
            "Accept": "application/json",
        }
        start = 0
        documents: list[SourceDocument] = []
        latest_cursor = since_cursor

        while True:
            params = {
                "type": "page",
                "start": start,
                "limit": self.page_size,
                "expand": "body.storage,version,metadata.labels",
            }
            url = f"{self.base_url}/rest/api/content?{urlencode(params)}"
            payload = self.http_get_json(url, headers, self.timeout_seconds)
            results = payload.get("results", [])

            for page in results:
                page_id = str(page.get("id", ""))
                title = str(page.get("title", "Confluence page"))
                storage_value = _extract_text(
                    (((page.get("body") or {}).get("storage") or {}).get("value"))
                )
                body = _strip_html(storage_value).strip() or title
                updated_at = str(((page.get("version") or {}).get("when", "")))

                if updated_at and not _is_newer(updated_at, since_cursor):
                    continue

                label_entries = (((page.get("metadata") or {}).get("labels") or {}).get("results")) or []
                labels = [str(entry.get("name", "")) for entry in label_entries if entry.get("name")]
                scope = _scope_from_labels(labels)
                if not scope:
                    scope = _scope_from_text(f"{title} {body}")
                if not scope:
                    scope = ["all"]

                documents.append(
                    SourceDocument(
                        source_id=f"CONF-{page_id}",
                        source_type="confluence",
                        title=title,
                        body=body,
                        team_scope=scope,
                        tags=[label for label in labels if label],
                    )
                )

                if updated_at:
                    if latest_cursor is None or _is_newer(updated_at, latest_cursor):
                        latest_cursor = updated_at

            if len(results) < self.page_size:
                break
            start += self.page_size

        return ConnectorFetchResult(documents=documents, next_cursor=latest_cursor)
