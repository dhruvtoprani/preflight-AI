# Pilot Baseline Metrics

Use this sheet-style checklist to capture the first pilot baseline. The goal is to measure whether PreFlight improves kickoff preparation, not to prove model quality in isolation.

## Metrics to Capture

| Metric | Definition | Collection Method | Target |
|---|---|---|---|
| Prep time before PreFlight | Minutes PM/TPM would normally spend gathering kickoff context | PM self-report before using PreFlight | Baseline only |
| Prep time with PreFlight | Minutes from structured brief start to usable kickoff agenda | Timer during pilot run | Downward trend |
| Actionable blocker detection | Count of blockers the PM agrees should be resolved before kickoff | PM review of output | At least 1 in 50%+ runs |
| Evidence-backed concern ratio | Evidence-backed concerns divided by total concerns | `make eval-pilot` or run payload | 30%+ for MVP signoff |
| Low-trust concern rate | Concerns marked incorrect, irrelevant, or unsupported by PM | PM review of output | Under 10% |
| Kickoff agenda usefulness | PM rating from 1-5 | Post-run survey | 4+ average |
| Owner map usefulness | PM rating from 1-5 | Post-run survey | 4+ average |

## Per-Run Capture Template

| Field | Value |
|---|---|
| Initiative title |  |
| Requester |  |
| Date |  |
| Teams included |  |
| Time to submit brief |  |
| Time to review output |  |
| Overall readiness |  |
| Actionable blockers found |  |
| Incorrect or low-trust concerns |  |
| Missing teams or context |  |
| Kickoff agenda rating (1-5) |  |
| Owner map rating (1-5) |  |
| Would use before next kickoff? |  |

## Eval Command

Run the canned pilot eval after any prompt, retrieval, or moderation change:

```bash
make eval-pilot
```

For release signoff, use the minimum evidence ratio gate:

```bash
EVAL_MIN_EVIDENCE_RATIO=0.30 make eval-pilot
```

The JSON report is written to `.tmp/pilot-eval/report.json`.
