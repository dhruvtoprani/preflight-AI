# PreFlight

**PreFlight is a Slack-native stakeholder context engine for PMs and TPMs.**

Before pulling six teams into a kickoff, a PM can drop an initiative brief in Slack and get an async multi-lens review across Engineering, QA, Design, Support, GTM, Security/Privacy, and TPM.

## Why This Is Useful
- Cuts pre-kickoff context gathering from hours to minutes.
- Surfaces blockers and cross-team dependencies early.
- Produces a kickoff-ready agenda and ownership map.
- Keeps humans focused on judgment, not scavenger-hunt discovery.

## What It Does Today
1. Accepts structured initiative briefs from Slack.
2. Runs role-based agent reviews (deterministic or LLM-backed).
3. Returns team concerns with evidence labels:
- `evidence-backed`
- `inferred`
- `needs confirmation`
4. Synthesizes overall readiness (`green/yellow/red`) plus blockers, questions, and next actions.
5. Persists runs and exposes run history + dashboard drilldown.

## End User Workflow
1. PM submits brief in Slack thread.
2. PreFlight runs multi-team review asynchronously.
3. Thread receives readiness summary and critical gaps.
4. PM walks into first discussion with a concrete, scoped agenda.

## Structured Slack Input
Use this format:

```text
title: ...
problem: ...
solution: ...
timeline: ...
teams: engineering, qa, design, security_privacy
metric: ...
constraints: ...
```

Team notes:
- Canonical teams: `engineering, qa, design, support, gtm, security_privacy, tpm`
- Alias mapping supported: `security/privacy`, `security`, `privacy`, `sec` -> `security_privacy`

## Quick Start (Local)
1. `make dev-up`
2. `make check-persistence`
3. `make run-local-stack`
4. `make seed-pilot`
5. `make eval-pilot`

Optional pilot signoff gate:
- `EVAL_MIN_EVIDENCE_RATIO=0.30 make eval-pilot`

## Repo Layout
- `apps/slack-bot`: Slack command/events intake + thread delivery.
- `apps/dashboard`: Run history overview + drilldown UI.
- `services/orchestrator`: Team review execution, synthesis, run APIs.
- `services/ingestion`: Document ingestion/index pipeline.
- `services/retrieval`: Context retrieval APIs.
- `packages/schemas`: Shared contracts.
- `packages/agent-prompts`: Team/moderator prompt templates.
- `docs`: Product, architecture, and delivery docs.

## Security Defaults
- `/runs*` APIs can require bearer token via `PREFLIGHT_HISTORY_API_TOKEN`.
- Run-history responses are redacted by default.

## MVP Positioning
PreFlight is **pre-meeting alignment intelligence**: a practical way for PM/TPM teams to pressure-test initiatives before kickoff and reduce coordination waste.
