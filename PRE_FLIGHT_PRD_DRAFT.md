# PreFlight PRD Draft v0.1

## 1. Document Control
- Product: PreFlight
- Version: v0.1 (Draft)
- Date: 2026-05-18
- Author: Working draft (Codex + founder)
- Status: Draft for alignment

## 2. Executive Summary
PreFlight is a Slack-native multi-agent initiative review system for PMs and TPMs. Before kickoff, users submit an initiative brief and receive role-based, evidence-grounded feedback on readiness, risks, dependencies, and unresolved decisions.

## 3. Background and Opportunity
Cross-functional projects often fail early due to avoidable alignment gaps: unclear ownership, hidden dependencies, unrealistic timelines, missing privacy/security checks, and poor release coordination. Existing workflows scatter context across systems and people. PreFlight compresses this discovery cycle asynchronously before meetings.

## 4. Goals
1. Deliver high-signal pre-kickoff readiness reviews in Slack.
2. Surface cross-functional blockers and unanswered questions early.
3. Improve initiative quality without adding meeting overhead.
4. Provide evidence-linked insights to increase trust.

## 5. Non-Goals
1. Autonomous project decision-making.
2. Employee simulation or personality replication.
3. Replacing project managers or stakeholder discussions.
4. Fully automated downstream execution in Jira/roadmap tools for MVP.

## 6. Users and Jobs-to-be-Done

### Primary Users
- PMs and TPMs initiating cross-functional efforts.

### Secondary Users
- Engineering, QA, Design, Support, GTM, Security/Privacy leads reviewing proposals.

### JTBD
- "Before I schedule a kickoff, help me identify blockers, missing owners, and unresolved decisions so the first meeting is productive."

## 7. User Stories
1. As a PM, I can submit a structured initiative brief in Slack and receive a multi-perspective readiness review.
2. As a TPM, I can identify sequencing and dependency risks before kickoff.
3. As a stakeholder lead, I can see evidence-backed concerns from my functional lens.
4. As a team, we can use a generated kickoff agenda and decision memo to accelerate alignment.

## 8. Functional Requirements

### FR-1 Initiative Intake
- Collect required fields:
  - title
  - problem statement
  - proposed solution
  - timeline
  - affected teams
  - success metric
  - known constraints
- Validate completeness and request missing fields.

### FR-2 Multi-Agent Review
- Run role-specific agents:
  - engineering, QA, design, support, GTM, security/privacy, TPM
- Use agent-scoped retrieval policies.
- Enforce structured response schema per agent.

### FR-3 Moderation and Synthesis
- Aggregate agent outputs.
- Produce overall readiness score (Green/Yellow/Red).
- Return blockers, dependencies, open questions, required artifacts, and owner suggestions.
- Draft recommended kickoff agenda.

### FR-4 Evidence and Trust Signals
- Attach evidence labels to every concern:
  - evidence-backed
  - inferred
  - needs confirmation
- Include confidence score and source references.

### FR-5 Slack-Native Delivery
- Post progress + final synthesis in a Slack thread.
- Keep outputs scannable and role-segmented.

### FR-6 Run Persistence
- Persist run metadata and outputs:
  - initiative brief
  - agent responses
  - synthesized summary
  - confidence/evidence metadata

## 9. Non-Functional Requirements
1. Performance: target <= 5 min full review completion.
2. Reliability: graceful partial failure if one agent times out.
3. Security: role-based source scoping and source allowlists.
4. Observability: latency, token/cost, confidence distribution, evidence coverage.
5. Extensibility: support adding future agents and data sources.

## 10. Information Architecture and Data Model (Initial)

### Core Entities
1. Workspace
2. Initiative
3. ReviewRun
4. AgentResponse
5. Concern
6. EvidenceReference
7. ActionItem
8. DecisionMemo

### Key Fields (Examples)
- Concern:
  - role
  - severity
  - statement
  - confidence
  - evidence_status
- EvidenceReference:
  - source_type
  - source_id
  - excerpt
  - retrieval_score

## 11. System Architecture (MVP)
1. Slack App (Bolt) receives command/mention.
2. FastAPI endpoint validates and creates run.
3. LangGraph orchestrates agent fan-out/fan-in.
4. Retrieval service resolves agent-scoped context from pgvector.
5. Moderator agent synthesizes final response.
6. Slack thread receives staged + final output.
7. Optional Next.js dashboard reads run history from Postgres.

## 12. MVP Scope Boundaries

### In Scope
1. Slack command + threaded output.
2. Seeded-doc ingestion pipeline.
3. 8 agents including moderator.
4. Evidence labels and confidence.
5. Green/Yellow/Red readiness output.

### Out of Scope (v0.1)
1. Deep Jira/Confluence write-backs.
2. Personalized individual-level AI personas.
3. Automated calendar scheduling.
4. Org-wide governance workflows.

## 13. Metrics and Success Criteria

### Activation
1. % of invited PM/TPM users who run at least one preflight.

### Engagement
1. Average runs per active PM/TPM per month.
2. % runs shared in stakeholder channels.

### Quality
1. User usefulness rating >= 70%.
2. Evidence-backed concerns ratio >= 80% for high-priority concerns.
3. Low-trust output reports <= 10%.

### Impact
1. % initiatives with blockers discovered pre-kickoff.
2. Reduction in kickoff rework incidents (pilot self-report).

## 14. Rollout Plan

### Milestone 1: Internal Prototype
- Slack workflow + static docs + 3 agents + moderator.
- One demo scenario end-to-end.

### Milestone 2: MVP Beta
- Full 8-agent review.
- Evidence labels and structured outputs.
- Basic observability.

### Milestone 3: Pilot
- 5-15 PM/TPM users.
- Weekly feedback loop.
- Prompt/policy hardening.

## 15. Risks and Mitigations
1. Hallucinations -> evidence status categories + citation requirements.
2. Sensitive data leakage -> strict source scopes + permission checks.
3. Overly verbose outputs -> concise schema + moderator compression.
4. Low adoption -> optimize intake UX and quality of kickoff agenda output.

## 16. Dependencies
1. Slack app setup and workspace permissions.
2. Seed data corpus preparation.
3. Model + embedding provider credentials.
4. Infrastructure for async execution and persistence.

## 17. Open Questions
1. Should readiness be categorical only or include numeric sub-scores?
2. What minimum evidence threshold gates a "Red" concern?
3. Slack-only MVP or dashboard in first release?
4. Which two integrations should be first after seeded docs (Jira vs Confluence)?

## 18. Launch Readiness Checklist (Draft)
1. End-to-end demo scenario validated.
2. Output quality rubric meets threshold.
3. Security/privacy review completed.
4. Pilot onboarding docs prepared.
5. Feedback instrumentation live.

## 19. Appendix A: Example Slack Output Shape
1. Overall readiness: Yellow
2. Top blockers (max 5)
3. Team concern cards by role
4. Open questions list
5. Suggested owners and next steps
6. Suggested kickoff agenda
7. Decision memo draft
