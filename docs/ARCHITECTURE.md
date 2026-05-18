# PreFlight Architecture (v0.1)

## High-Level Flow
1. PM invokes `@PreFlight` in Slack with initiative brief.
2. Slack bot validates payload and opens a `ReviewRun`.
3. Orchestrator fans out to role agents.
4. Each role agent retrieves from scoped context partitions.
5. Agent outputs normalize into shared schema.
6. Moderator synthesizes readiness, blockers, and next actions.
7. Final response posts in Slack thread and persists to DB.

## Component Boundaries
- Slack bot: transport + UX.
- Orchestrator: workflow control + aggregation.
- Retrieval: context access abstraction.
- Ingestion: source parsing/chunking/indexing.
- Schemas: system contracts and compatibility.

## Design Constraints
1. Avoid tight coupling to one model provider.
2. Keep retrieval and orchestration independently testable.
3. All outputs must include confidence + evidence status.
4. Persist intermediate artifacts for traceability.

## Data Model (Core)
- `InitiativeBrief`
- `ReviewRun`
- `AgentReview`
- `Concern`
- `EvidenceReference`
- `ModeratorSummary`
