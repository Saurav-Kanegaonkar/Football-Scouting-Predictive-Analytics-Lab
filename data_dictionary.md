# Data Dictionary

| Table | Grain | Purpose |
|---|---|---|
| `data/match_manifest.csv` | Match | Public MLS match inventory, scores, event-row counts, and lineup counts. |
| `data/player_match_features.csv` | Player match | Event-derived football features used for model training and player scoring. |
| `analysis/outputs/scouting_priority_queue.csv` | Player profile | Ranked player review queue with model probability, review priority, confidence, sample risk, and next action. |
| `analysis/outputs/model_diagnostics.json` | Model run | Target definition, role medians, holdout metrics, and feature weights. |
| `analysis/outputs/data_quality_checks.csv` | Check | Data coverage and workflow readiness checks. |
| `analysis/outputs/agentic_scouting_briefs.md` | Brief | Generated stakeholder summaries for the highest-priority player rows. |
| `analysis/outputs/app_payload.json` | Portfolio UI payload | Static app data assembled from the generated outputs. |
