import csv
from collections import defaultdict

daily = defaultdict(lambda: {"risk": 0.0, "quality": 0.0, "rows": 0})
with open("data/daily_metrics.csv", newline="") as f:
    for row in csv.DictReader(f):
        bucket = daily[row["entity_id"]]
        bucket["risk"] += float(row["risk_score"])
        bucket["quality"] += float(row["quality_score"])
        bucket["rows"] += 1

impact = defaultdict(float)
with open("data/source_events.csv", newline="") as f:
    for row in csv.DictReader(f):
        impact[row["entity_id"]] += float(row["estimated_impact"])

ranked = []
for entity_id, values in daily.items():
    risk = values["risk"] / values["rows"]
    quality = values["quality"] / values["rows"]
    score = risk * 0.62 + (100 - quality) * 0.32 + impact[entity_id] / 14000
    ranked.append((score, entity_id, risk, quality, impact[entity_id]))

for score, entity_id, risk, quality, event_impact in sorted(ranked, reverse=True)[:10]:
    print(f"{entity_id}: priority_score={score:.1f}, risk={risk:.1f}, quality={quality:.1f}, event_impact=$" + format(event_impact, ",.0f"))
