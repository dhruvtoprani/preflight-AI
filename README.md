# PreFlight

## Product Summary
**PreFlight is a Slack-native stakeholder context engine for PMs and TPMs.**

It helps teams pressure-test initiatives before kickoff by running async multi-agent reviews grounded in role-scoped context from internal systems, including **Jira and Confluence**.

## Problem
Kickoff quality is often low because PMs and TPMs spend too much time collecting fragmented context across teams.

Common failure mode:
1. The first meeting is used to discover basic blockers.
2. Dependencies are surfaced late.
3. Timeline risk appears after alignment has already started.

## Outcome
PreFlight gives PM/TPM teams **pre-meeting alignment intelligence**:
- Readiness signal (`green/yellow/red`)
- Team-specific risks and blockers
- Questions to resolve before kickoff
- Suggested owner map + first-meeting agenda

## Users
- Primary: PMs, TPMs
- Secondary: Engineering managers, QA leads, Design leads, Support leads, GTM, Security/Privacy

## Core Workflow
1. PM submits a structured initiative brief in Slack.
2. PreFlight runs role-based team reviews in parallel.
3. A moderator synthesizes concerns and recommends next actions.
4. PM enters kickoff with concrete risks, owners, and sequencing questions.

## MVP Scope (Implemented)
- Slack intake (`/slack/command` + events) with strict structured validation.
- Multi-agent orchestration:
  - deterministic fallback mode
  - LLM-driven mode
- Team-scoped retrieval and prompt policies.
- Evidence labels per concern:
  - `evidence-backed`
  - `inferred`
  - `needs confirmation`
- Run persistence + history APIs + dashboard drilldown.

## Team Lenses + Jira/Confluence Integration
PreFlight supports the following role lenses:
- `engineering`
- `qa`
- `design`
- `support`
- `gtm`
- `security_privacy`
- `tpm`

Each team lens is configured with scoped context policy (`focus_areas`, `preferred_sources`, `retrieval_hints`).

**Jira + Confluence integration is available and used as first-class context sources** for team reviews (with per-team source preferences). Example policy directions:
- Engineering: Jira + Confluence + architecture/roadmap context
- QA: Jira + Confluence + release/bug context
- Support: Jira + Confluence + support/help context
- TPM: Jira + Confluence + roadmap/release-calendar context

## Integrations
### Live connectors (implemented)
- Jira API ingestion
- Confluence API ingestion
- Checkpointed sync for incremental updates

### Seed / dump path (implemented)
- Local JSON exports for rapid pilot setup and demos

### Additional sources (planned/expandable)
- Google Drive, support tooling, release calendars, additional knowledge systems

## Slack Brief Format
Use this shape:

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
- Supported aliases: `security/privacy`, `security`, `privacy`, `sec` -> `security_privacy`

## Local Run
1. `make dev-up`
2. `make check-persistence`
3. `make run-local-stack`
4. `make seed-pilot`
5. `make eval-pilot`

Optional pilot signoff gate:
- `EVAL_MIN_EVIDENCE_RATIO=0.30 make eval-pilot`

## Security Defaults
- `/runs*` endpoints can be token-protected via `PREFLIGHT_HISTORY_API_TOKEN`.
- Run-history payloads are redacted by default.

## Repository Layout
- `apps/slack-bot`: Slack interaction + response delivery
- `apps/dashboard`: run history + drilldown UI
- `services/orchestrator`: orchestration + moderation + run APIs
- `services/ingestion`: Jira/Confluence/seed ingestion pipeline
- `services/retrieval`: context retrieval service
- `packages/schemas`: shared contracts
- `packages/agent-prompts`: role prompt templates
- `docs`: architecture, scope, action items

## Product Positioning
PreFlight reduces low-value discovery work and helps teams spend human time on judgment, tradeoffs, and decisions.
