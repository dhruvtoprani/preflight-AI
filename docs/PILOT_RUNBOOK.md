# PreFlight Pilot Runbook

This runbook gives a PM/TPM enough structure to run the first PreFlight pilot without engineering support in the room.

## Pilot Goal

Validate whether PreFlight makes kickoff preparation faster and more complete by surfacing blockers, dependencies, owners, and evidence-backed questions before the first cross-functional meeting.

## Pilot Audience

- 3-5 PMs or TPMs running active initiatives.
- At least one initiative with engineering + QA involvement.
- At least one initiative with go-to-market, support, security/privacy, or migration risk.

## Before the Pilot

1. Confirm the pilot workspace has the expected local services:
   ```bash
   make lint
   make test
   make eval-pilot
   ```
2. Seed or sync context:
   ```bash
   make seed-pilot
   ```
3. Start services for the Slack + dashboard flow:
   ```bash
   make run-local-stack
   ```
4. Share the structured Slack brief format from `README.md` with pilot users.
5. Ask each pilot user to bring one real initiative that is 1-3 weeks before kickoff.

## Live Pilot Flow

1. PM posts a structured initiative brief in Slack.
2. PreFlight returns a threaded readiness review.
3. PM scans the output and marks:
   - useful blockers
   - missing context
   - incorrect or low-trust concerns
   - owner map gaps
4. PM uses the kickoff agenda in the next planning meeting.
5. Pilot owner records the baseline metrics in `docs/PILOT_BASELINE_METRICS.md`.

## Demo Flow

Use the canned briefs in `docs/pilot/demo_briefs/` when a live initiative is not available.

Recommended order:

1. `automated_pet_health_alerts.json`
2. `release_timeline_compression.json`
3. `cross_functional_migration_kickoff.json`

Run all three:

```bash
make eval-pilot
```

Optional signoff threshold:

```bash
EVAL_MIN_EVIDENCE_RATIO=0.30 make eval-pilot
```

## Signoff Checklist

- All services start locally.
- Demo briefs validate against `InitiativeBrief`.
- `make lint` passes.
- `make test` passes.
- `make eval-pilot` produces three runs.
- Pilot owner has recorded baseline metrics.
- PM/TPM pilot users understand that PreFlight is advisory and evidence-labeled, not an approval authority.

## Escalation Notes

- If Slack intake rejects a brief, check required fields and team aliases in `README.md`.
- If run history is missing, run `make check-persistence` and inspect file fallback under `PREFLIGHT_RUN_DIR` or `data/review_runs`.
- If evidence quality is low, refresh seeded/live context before changing prompts.
