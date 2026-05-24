# Analysis Plan

1. Load the public StatsBomb MLS 2023 match, lineup, and event JSON files.
2. Build player-match rows for every player with minutes and event activity.
3. Engineer role-aware football features from shots, xG, passes, carries, pressure, recovery, duel, dribble, and turnover events.
4. Define an explainable contribution index that balances attacking value, progression, pressure, defensive activity, and ball-security risk.
5. Train a lightweight logistic model on repeated appearances to predict whether the next appearance clears the player's role median contribution level.
6. Score all player profiles, including one-match profiles, while flagging small samples separately from model probability.
7. Rank the player review queue by model probability, contribution index, minutes, sample confidence, and turnover penalty.
8. Generate stakeholder briefs and data quality checks from the same outputs used by the UI.
