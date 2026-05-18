# PreFlight Readiness Scoring Spec (v0.1)

## Purpose
Provide a deterministic and explainable readiness decision for MVP while richer scoring evolves.

## Inputs
- `AgentReview.readiness` from each participating team agent.
- Optional concern metadata for future weighted scoring.

## Output
- `overall_readiness` in `{green, yellow, red}`.

## Deterministic Rule (Current)
1. If **any** team reports `red`, overall is `red`.
2. Else if any team reports `yellow`, overall is `yellow`.
3. Else overall is `green`.
4. If no team reviews are present, default to `green`.

## Why This Rule
- Easy to explain to PM/TPM users.
- Preserves high-signal risk surfacing from any role.
- Avoids opaque weighted heuristics in MVP.

## Planned Evolution (Post-MVP)
1. Severity-weighted concern scoring.
2. Confidence-weighted readiness.
3. Source quality weighting (e.g., release notes > stale docs).
4. Time-aware load and dependency pressure adjustments.
