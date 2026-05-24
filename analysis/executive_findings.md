# Executive Findings

## What I Analyzed

The pipeline processed six public MLS 2023 matches from StatsBomb Open Data, including 21,786 event rows and 186 player-match rows with event activity. The model trained on 68 repeated-appearance rows and scored 63 player profiles for review.

## Findings

- The top of the queue is driven by progressive passing, defensive action rate, duels, and ball progression rather than raw shot volume alone.
- One-match players can rank highly on event impact, but the artifact separates model score from data risk so stakeholders do not overread small samples.
- The holdout test is intentionally modest because the public MLS sample is small. The model is best interpreted as an explainable scouting triage method, not as a production-grade recruitment model.
- The highest-priority rows resolve into distinct actions: scout video packet, analyst review, monitor sample, or collect more minutes.

## Recommendation

Use the scouting queue as a first-pass review tool. The next analyst step would be to pair the top profiles with video clips, contract and availability context, physical profile data, and a larger event sample before any recruitment recommendation.
