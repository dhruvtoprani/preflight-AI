# PreFlight Project Scope (Working Reference)

## 1) Project Summary
**Product:** PreFlight  
**Tagline:** Slack-native multi-agent initiative review for PMs and TPMs  
**Core value:** Pre-meeting alignment intelligence that surfaces blockers, dependencies, and missing decisions before kickoff.

## 2) Problem Statement
PMs and TPMs lose significant time gathering scattered context (Jira, Confluence, roadmap docs, release notes, support trends) before they can run useful cross-functional kickoff meetings.

## 3) Product Goals
1. Reduce time spent on pre-kickoff context gathering.
2. Improve kickoff readiness quality by surfacing blockers early.
3. Give role-specific feedback from multiple stakeholder lenses.
4. Ground recommendations in evidence with confidence and status labels.
5. Keep humans in control of decisions while automating discovery and synthesis.

## 4) Non-Goals (MVP)
1. Replacing decision-making by humans.
2. Mimicking individual employees or "digital twins." 
3. Full enterprise-wide autonomous planning and execution.
4. Deep bi-directional write automation into Jira/Confluence in v1.

## 5) Target Users
1. Primary: PMs, TPMs.
2. Secondary: Eng Managers, QA leads, Design leads, Support leads, GTM leads.
3. Economic buyer (later): Product/Engineering leadership, PMO/TPMO.

## 6) Core User Workflow (MVP)
1. PM invokes `@PreFlight` in Slack with initiative brief template.
2. PreFlight parses required fields and flags missing info.
3. Orchestrator runs role/team agents with scoped context.
4. Agents return:
   - readiness signal
   - concerns
   - blockers/dependencies
   - questions to resolve
   - evidence labels (`evidence-backed`, `inferred`, `needs confirmation`)
5. Moderator synthesizes:
   - overall readiness (Green/Yellow/Red)
   - top blockers
   - required artifacts/owners
   - suggested kickoff agenda
   - short decision memo draft
6. Output posts in Slack thread and optionally dashboard record.

## 7) MVP Inputs
1. Initiative title
2. Problem statement
3. Proposed solution
4. Target timeline
5. Affected teams
6. Success metric
7. Known constraints

## 8) MVP Outputs
1. Overall readiness status: Green / Yellow / Red
2. Team-specific feedback cards
3. Blockers and dependencies list
4. Questions to resolve before kickoff
5. Suggested owners and next actions
6. Kickoff agenda draft
7. Decision memo draft

## 9) Agent Set (MVP)
1. Engineering Agent
2. QA Agent
3. Design Agent
4. Support Agent
5. GTM Agent
6. Security/Privacy Agent
7. TPM Agent
8. Moderator Agent

## 10) System Components / Moving Parts
1. **Slack App Layer**
   - slash command / mention handling
   - threaded response UX
   - initiative input capture
2. **Orchestration Layer**
   - multi-agent workflow graph
   - retries, timeouts, partial-failure handling
3. **Context Retrieval Layer**
   - document ingestion pipeline
   - chunking + embeddings
   - agent-scoped retrieval policies
4. **Knowledge/Data Layer**
   - relational data (initiatives, runs, outputs)
   - vector store for retrieval
   - audit/event logs
5. **Policy & Safety Layer**
   - source allowlist
   - role-based access controls
   - prompt/version controls
6. **Presentation Layer**
   - Slack thread responses
   - optional web dashboard for run history and artifacts
7. **Observability Layer**
   - quality telemetry
   - latency/cost tracking
   - hallucination/evidence coverage metrics

## 11) Proposed Tech Stack (MVP)
1. Slack Bolt SDK (Slack integration)
2. FastAPI (backend API + orchestration entrypoints)
3. LangGraph (multi-agent orchestration)
4. Supabase Postgres + pgvector (state + retrieval)
5. LlamaIndex (ingestion/retrieval abstractions)
6. Redis or Trigger.dev (background jobs)
7. Next.js (optional dashboard)
8. OpenAI models for agent + moderation steps

## 12) Data Sources (MVP vs Later)
**MVP (seeded docs / exports):**
1. Confluence exports
2. Jira exports
3. Roadmap docs
4. Release calendar
5. Team capacity notes
6. Decision logs
7. Architecture notes
8. Support ticket summaries

**Later integrations:**
1. Jira API
2. Confluence API
3. Google Drive
4. GitHub
5. Linear
6. Notion
7. Slack history
8. Google Calendar

## 13) Evidence Model (Critical Feature)
Each concern includes:
1. Concern statement
2. Evidence summary
3. Evidence source references
4. Confidence score (0-1)
5. Evidence status:
   - evidence-backed
   - inferred
   - needs confirmation

## 14) Key Risks + Mitigations
1. **Hallucinated concerns**
   - Mitigation: evidence labels + source citations + confidence thresholding
2. **Security/privacy leakage**
   - Mitigation: agent-scoped retrieval + RBAC + source allowlists
3. **Too much output noise**
   - Mitigation: strict response schema + moderator compression
4. **Low trust from teams**
   - Mitigation: transparent citations + "needs confirmation" category + human override
5. **Integration complexity early**
   - Mitigation: start with static seeded docs before live APIs

## 15) Success Criteria

### Product Outcomes
1. PM/TPM reports improved kickoff preparedness.
2. Fewer kickoff meetings blocked by missing owners/dependencies.
3. Higher pre-meeting clarity scores from cross-functional stakeholders.

### MVP Quantitative Targets (Pilot)
1. <= 5 minutes end-to-end analysis latency per initiative.
2. >= 80% of high-priority concerns contain explicit evidence labels.
3. >= 70% user-rated usefulness on initial pilot runs.
4. >= 50% of runs produce at least one actionable blocker found pre-kickoff.
5. <= 10% runs flagged as "low trust / unclear evidence."

## 16) Action Items (Execution Plan)

### Phase 0: Foundation (Week 1)
1. Define initiative input schema and output JSON schema.
2. Implement seeded ingestion pipeline from local files.
3. Define agent prompts, role scopes, and retrieval boundaries.
4. Set up database schema for runs, concerns, evidence, decisions.

### Phase 1: Core MVP (Weeks 2-4)
1. Build Slack app command + thread interaction.
2. Implement LangGraph orchestrator with 8 agents.
3. Build role-scoped retrieval wrappers.
4. Implement moderator synthesis and readiness scoring.
5. Add evidence labels and source links.

### Phase 2: Pilot Readiness (Weeks 5-6)
1. Add run history dashboard (minimal).
2. Add observability: latency, cost, confidence, evidence coverage.
3. Create 10-15 realistic scenario test briefs.
4. Conduct pilot with PM/TPM users and collect rubric feedback.

### Phase 3: Hardening (Weeks 7-8)
1. Improve prompt quality and false-positive handling.
2. Add security/privacy policy checks.
3. Add exportable decision memo and kickoff packet.
4. Prepare demo narrative and sample workspace.

## 17) Open Decisions
1. Single workspace vs multi-workspace tenancy model in v1?
2. Strict deterministic scoring vs model-judged readiness scoring?
3. Dashboard in MVP or Slack-only first?
4. Live integrations timeline (Jira/Confluence API) vs export-only for pilot?
5. Pricing signal for beta: seat-based vs workspace usage-based?

## 18) Immediate Next Steps (This Week)
1. Finalize PRD v0.1 from this scope.
2. Lock MVP schema for input/output.
3. Build one end-to-end happy path using seeded docs.
4. Demo in Slack thread format with one sample initiative.
