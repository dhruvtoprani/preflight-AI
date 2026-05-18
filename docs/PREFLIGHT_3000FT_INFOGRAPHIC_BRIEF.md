# PreFlight 3000-ft Infographic Brief

## 1) One-Screen Executive Summary
- **Product:** PreFlight
- **Category:** Slack-native, multi-agent initiative readiness review
- **Audience:** PMs and TPMs leading cross-functional initiatives
- **Core Promise:** Before kickoff, surface blockers, missing owners, dependencies, and open questions with evidence-backed stakeholder perspectives.
- **Output:** A threaded readiness review with Green/Yellow/Red status, team concerns, and an actionable kickoff plan.

## 2) Problem at 3000 ft
PMs/TPMs spend too much time stitching context across Jira, Confluence, roadmaps, support insights, and release calendars before they can run a useful kickoff.

**Current failure mode:**
- Discovery happens live in meetings
- Hidden dependencies appear late
- Ownership is unclear
- Kickoff meetings become context gathering instead of decision making

**PreFlight shift:**
- Move discovery async before the meeting
- Preserve cross-functional tension via role-specific agents
- Let humans spend meeting time on judgment and tradeoffs

## 3) Strategic Framing (Important)
### What PreFlight is
- Pre-meeting alignment intelligence
- Async stakeholder review before kickoff
- Context compression engine for PM/TPM workflows

### What PreFlight is not
- Employee digital twins
- Autonomous project decision maker
- Replacement for PMs/TPMs or stakeholder input

## 4) Product Outcomes
### Primary Outcomes
1. Faster kickoff preparation
2. Better first-meeting quality
3. Earlier blocker detection
4. Clearer ownership and dependency mapping
5. Higher trust through evidence labels

### Pilot Targets
1. <= 5 minutes end-to-end review latency
2. >= 80% evidence labels on high-priority concerns
3. >= 70% user-rated usefulness
4. >= 50% runs reveal at least one actionable blocker pre-kickoff
5. <= 10% low-trust output reports

## 5) User Stories (Infographic-ready)
1. **PM story:** "As a PM, I can submit an initiative brief in Slack and get a multi-team readiness readout before scheduling kickoff."
2. **TPM story:** "As a TPM, I can identify sequencing and dependency risks early and convert them into owner-assigned actions."
3. **Stakeholder lead story:** "As a functional lead, I can review concerns in my lens with explicit evidence and confidence signals."
4. **Leadership story:** "As leadership, I can see whether initiatives are discussion-ready versus blocked by unresolved fundamentals."

## 6) MVP Scope (What’s in)
### Inputs
- Initiative title
- Problem statement
- Proposed solution
- Target timeline
- Affected teams
- Success metric
- Known constraints

### Outputs
- Overall readiness: Green / Yellow / Red
- Team-specific concerns
- Blockers and dependencies
- Questions to resolve
- Suggested owners
- Suggested kickoff agenda
- Decision memo draft

### Agents (MVP)
- Engineering
- QA
- Design
- Support
- GTM
- Security/Privacy
- TPM
- Moderator

## 7) System Layers (Architecture Slice)
1. **Interaction Layer (Slack App):** mention/command intake + thread output UX
2. **Orchestration Layer:** agent fan-out/fan-in, retries, partial-failure handling
3. **Retrieval Layer:** role-scoped context retrieval policies
4. **Ingestion Layer:** document parsing, chunking, indexing
5. **Data Layer:** Postgres state, pgvector retrieval memory, event logs
6. **Policy & Trust Layer:** source allowlists, RBAC, evidence labeling
7. **Presentation Layer:** Slack response formatting + optional dashboard
8. **Observability Layer:** latency, cost, confidence distribution, evidence coverage

## 8) Tech Stack (Current/Target)
### Current implementation direction
- Python services
- FastAPI for service endpoints
- Shared Pydantic schema contracts
- Dockerized local infra (Postgres+pgvector, Redis)

### MVP target stack
- Slack Bolt SDK (Slack integration)
- FastAPI (backend APIs)
- LangGraph (multi-agent orchestration)
- Supabase Postgres + pgvector (state + retrieval)
- LlamaIndex (ingestion/retrieval abstractions)
- Redis or Trigger.dev (async jobs)
- OpenAI/Anthropic models (agent reasoning)
- Optional Next.js dashboard (run history + artifacts)

## 9) End-to-End Workflow (Swimlane Summary)
1. PM posts initiative brief in Slack
2. PreFlight validates input and creates `ReviewRun`
3. Orchestrator invokes role agents
4. Each role agent retrieves scoped context
5. Agents return structured concerns + evidence metadata
6. Moderator synthesizes readiness + action plan
7. Slack thread receives final review output
8. Run artifacts persist for traceability and replay

## 10) Trust & Safety Model (Key Differentiator)
### Evidence Labeling
Each concern includes:
- concern statement
- evidence reference(s)
- confidence score
- status: `evidence-backed`, `inferred`, or `needs confirmation`

### Governance posture
- Scoped retrieval by role/team
- Human decision ownership preserved
- Source transparency over black-box answers

## 11) Why This Beats Generic RAG
### Generic RAG
- One question -> one answer

### PreFlight
- One initiative -> multi-perspective review
- Preserves conflict between team lenses
- Synthesizes decision readiness, not just raw facts
- Produces action-oriented kickoff prep artifacts

## 12) Data Sources
### MVP first
- Confluence exports
- Jira exports
- Roadmap docs
- Release calendar
- Team capacity notes
- Decision logs
- Architecture notes
- Support ticket summaries

### Later integrations
- Jira API
- Confluence API
- Google Drive
- GitHub
- Linear
- Notion
- Slack history
- Google Calendar

## 13) Build Status Snapshot (as of 2026-05-18)
### Completed
- Product scope + PRD draft
- Scalable monorepo scaffold
- Shared contracts package
- Orchestrator/Slack/ingestion/retrieval service stubs
- Batch A complete:
  - Makefile
  - schema contract tests and fixtures
  - readiness scoring spec
  - pluggable `AgentRunner` abstraction
  - tests passing

### Next
- Batch B: first vertical slice (Slack intake -> orchestrator -> formatted output)
- Batch C: retrieval/evidence quality hardening

## 14) Roadmap (Infographic Timeline)
1. **Foundation (done):** contracts + scaffold + deterministic scoring
2. **Vertical Slice (next):** real Slack-to-review flow + persistence fallback + graceful partial failure
3. **Retrieval Quality:** seeded ingestion + role-scoped evidence retrieval
4. **Pilot Readiness:** observability + scenario packs + PM/TPM pilot loop
5. **Hardening:** policy checks, better scoring, richer integrations

## 15) Risks and Mitigations
1. **Hallucinated concerns** -> evidence labels + source references + confidence
2. **Data leakage concerns** -> scoped retrieval + RBAC + source allowlists
3. **Output noise** -> strict response schema + moderator compression
4. **Adoption risk** -> Slack-native UX + kickoff agenda utility

## 16) Suggested Infographic Layout (Practical)
1. **Top banner:** Name + one-liner + positioning
2. **Left column:** problem and current pain
3. **Center:** architecture layers + workflow arrows
4. **Right column:** outputs + user stories + trust model
5. **Bottom:** metrics targets + roadmap timeline + current status marker

## 17) Copy Blocks You Can Reuse Verbatim
- "Before kickoff, PreFlight runs async stakeholder reviews so PMs and TPMs walk into meetings with blockers, dependencies, and owner gaps already visible."
- "PreFlight does not replace stakeholder judgment; it accelerates cross-functional context discovery."
- "Evidence-labeled concerns make readiness transparent: evidence-backed, inferred, or needs confirmation."

