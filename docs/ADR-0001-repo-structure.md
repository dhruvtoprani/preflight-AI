# ADR-0001: Monorepo Structure for PreFlight

## Status
Accepted (2026-05-18)

## Context
PreFlight combines Slack UX, orchestration, retrieval, ingestion, and shared contracts. A fragmented repo layout risks contract drift and weak integration testing.

## Decision
Use a single monorepo with clear boundaries:
- apps
- services
- shared packages
- infra
- docs

## Consequences
Positive:
1. Shared contracts can be versioned centrally.
2. Faster local end-to-end iteration.
3. Easier CI composition for integration checks.

Tradeoff:
1. Requires disciplined ownership boundaries.
