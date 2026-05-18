from __future__ import annotations

import os
import tempfile
from pathlib import Path

from shared_utils.run_store import ReviewRunStore

from .team_policies import load_team_policies


def _bool_status(value: bool) -> str:
    return "ok" if value else "missing"


def build_full_health_payload() -> dict:
    runner_mode = os.getenv("PREFLIGHT_RUNNER_MODE", "auto")
    llm_key_present = bool(os.getenv("OPENAI_API_KEY"))

    default_policy_path = (
        Path(__file__).resolve().parents[2] / "config" / "team_context_policies.json"
    )
    policy_path = Path(os.getenv("PREFLIGHT_TEAM_POLICY_PATH", default_policy_path))

    default_template_dir = (
        Path(__file__).resolve().parents[4] / "packages" / "agent-prompts" / "templates"
    )
    template_dir = Path(os.getenv("PREFLIGHT_PROMPT_TEMPLATE_DIR", default_template_dir))

    index_default = Path(tempfile.gettempdir()) / "preflight-ai" / "seed_documents.jsonl"
    index_path = Path(os.getenv("PREFLIGHT_INDEX_PATH", index_default))

    jira_configured = bool(
        os.getenv("JIRA_BASE_URL") and os.getenv("JIRA_EMAIL") and os.getenv("JIRA_API_TOKEN")
    )
    confluence_configured = bool(
        os.getenv("CONFLUENCE_BASE_URL")
        and os.getenv("CONFLUENCE_EMAIL")
        and os.getenv("CONFLUENCE_API_TOKEN")
    )

    policies_loaded = load_team_policies(policy_path=policy_path)

    check_db = os.getenv("PREFLIGHT_PERSISTENCE_HEALTH_DB_CHECK", "false").lower() == "true"
    persistence = ReviewRunStore().persistence_diagnostics(check_connection=check_db)

    checks = {
        "llm_key": _bool_status(llm_key_present),
        "team_policy_file": _bool_status(policy_path.exists()),
        "prompt_templates_dir": _bool_status(template_dir.exists()),
        "index_file": _bool_status(index_path.exists()),
        "jira_connector_config": _bool_status(jira_configured),
        "confluence_connector_config": _bool_status(confluence_configured),
        "persistence": persistence["status"],
    }

    status = "ok"
    if (
        checks["team_policy_file"] != "ok"
        or checks["prompt_templates_dir"] != "ok"
        or checks["persistence"] != "ok"
    ):
        status = "degraded"

    return {
        "status": status,
        "service": "orchestrator",
        "runner_mode": runner_mode,
        "checks": checks,
        "policies_loaded": len(policies_loaded),
        "paths": {
            "team_policy": str(policy_path),
            "prompt_template_dir": str(template_dir),
            "index_path": str(index_path),
            "run_dir": persistence.get("run_dir"),
        },
        "persistence": persistence,
    }
