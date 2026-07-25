# Demo Brief Expected Outcomes

These snapshots describe the expected deterministic-mode shape for each canned demo brief. Exact run IDs and timestamps vary.

## Automated Pet Health Alerts

- Expected readiness: `red`
- Teams: engineering, QA, support, TPM
- Expected blocker themes:
  - API ownership for notification workflows
  - QA test matrix for notification and onboarding regression risk
  - Support-readiness ownership
  - Owner/dependency map completion
- Expected evidence posture: engineering and QA should include evidence-backed source context; support and TPM may be inferred until seeded context is expanded.

## Release Timeline Compression

- Expected readiness: `red`
- Teams: engineering, QA, GTM, TPM
- Expected blocker themes:
  - API or technical ownership clarity
  - QA capacity/test matrix risk
  - Launch milestone and messaging dependency alignment
  - Cross-team sequencing and owner map
- Expected evidence posture: engineering and QA should remain evidence-backed; GTM/TPM concerns should be treated as inferred unless live context supports them.

## Cross-Functional Migration Kickoff

- Expected readiness: `yellow`
- Teams: engineering, security/privacy, support, TPM
- Expected blocker themes:
  - API or subsystem ownership clarity
  - Security/privacy review scope
  - Support escalation readiness
  - Migration owner/dependency map
- Expected evidence posture: engineering should include evidence-backed source context; security/privacy, support, and TPM may be inferred until migration-specific Jira/Confluence context is synced.

## Regression Signal

If these shapes change, inspect:

1. team selection and alias normalization in `orchestrator.runners`
2. deterministic runner concern generation
3. moderator readiness synthesis
4. seeded or live context changes
