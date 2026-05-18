from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

import tests.bootstrap  # noqa: F401
from ingestion.connectors import ConfluenceConnector, JiraConnector


class LiveConnectorTests(unittest.TestCase):
    def test_jira_connector_paginates_and_extracts_scope(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout: int) -> dict:
            query = parse_qs(urlparse(url).query)
            start_at = int(query.get("startAt", ["0"])[0])
            if start_at == 0:
                return {
                    "total": 2,
                    "issues": [
                        {
                            "key": "JIRA-101",
                            "fields": {
                                "summary": "API ownership unclear",
                                "description": "Need clear owner before kickoff.",
                                "updated": "2026-05-18T10:00:00.000+0000",
                                "labels": ["team:engineering", "dependency"],
                            },
                        }
                    ],
                }
            return {
                "total": 2,
                "issues": [
                    {
                        "key": "JIRA-102",
                        "fields": {
                            "summary": "QA matrix missing",
                            "description": {"text": "QA test matrix still unestimated."},
                            "updated": "2026-05-18T11:00:00.000+0000",
                            "labels": ["team:qa"],
                        },
                    }
                ],
            }

        connector = JiraConnector(
            base_url="https://example.atlassian.net",
            email="test@example.com",
            api_token="token",
            page_size=1,
            http_get_json=fake_get,
        )

        result = connector.fetch_updates()

        self.assertEqual(len(result.documents), 2)
        self.assertEqual(result.documents[0].source_type, "jira")
        self.assertIn("engineering", result.documents[0].team_scope)
        self.assertEqual(result.next_cursor, "2026-05-18T11:00:00.000+0000")

    def test_confluence_connector_filters_by_since_cursor(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout: int) -> dict:
            query = parse_qs(urlparse(url).query)
            start = int(query.get("start", ["0"])[0])
            if start == 0:
                return {
                    "results": [
                        {
                            "id": "77",
                            "title": "team:qa Regression checklist",
                            "body": {"storage": {"value": "<p>QA ready checklist</p>"}},
                            "version": {"when": "2026-05-18T08:00:00.000+0000"},
                            "metadata": {"labels": {"results": [{"name": "scope:qa"}]}},
                        }
                    ]
                }
            return {"results": []}

        connector = ConfluenceConnector(
            base_url="https://example.atlassian.net/wiki",
            email="test@example.com",
            api_token="token",
            page_size=1,
            http_get_json=fake_get,
        )

        result = connector.fetch_updates(since_cursor="2026-05-18T09:00:00.000+0000")

        self.assertEqual(len(result.documents), 0)
        self.assertEqual(result.next_cursor, "2026-05-18T09:00:00.000+0000")


if __name__ == "__main__":
    unittest.main()
