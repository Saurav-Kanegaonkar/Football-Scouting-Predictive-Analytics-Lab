import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOTS = [
    ROOT / "data" / "raw" / "statsbomb-open-data",
    Path("/private/tmp/statsbomb-open-data"),
]
MATCH_PATH = Path("data/matches/44/107.json")
OUTPUT_DIR = ROOT / "analysis" / "outputs"

EVENT_TYPES = [
    "Pass",
    "Carry",
    "Shot",
    "Pressure",
    "Ball Recovery",
    "Interception",
    "Duel",
    "Dribble",
    "Block",
    "Clearance",
    "Foul Won",
    "Foul Committed",
    "Dispossessed",
    "Miscontrol",
]

FEATURE_COLUMNS = [
    "shots_p90",
    "xg_p90",
    "passes_p90",
    "progressive_passes_p90",
    "carries_p90",
    "progressive_carries_p90",
    "pressures_p90",
    "recoveries_p90",
    "defensive_actions_p90",
    "duels_p90",
    "dribble_success_rate",
    "turnovers_p90",
]


def raw_root():
    for root in RAW_ROOTS:
        if (root / MATCH_PATH).exists():
            return root
    raise FileNotFoundError(
        "StatsBomb MLS 2023 files were not found. Expected a sparse checkout "
        "at data/raw/statsbomb-open-data or /private/tmp/statsbomb-open-data."
    )


def read_json(path):
    return json.loads(path.read_text())


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(value):
    return round(value * 100, 1)


def seconds_from_stamp(stamp):
    if not stamp:
        return 0
    minutes, seconds = stamp.split(":")[:2]
    return int(minutes) * 60 + int(float(seconds))


def minutes_from_positions(positions):
    total_seconds = 0
    for item in positions:
        start = seconds_from_stamp(item.get("from", "00:00"))
        end = seconds_from_stamp(item.get("to")) if item.get("to") else 96 * 60
        total_seconds += max(0, end - start)
    return max(0, min(102, total_seconds / 60))


def role_bucket(position):
    if not position:
        return "Unknown"
    position = position.lower()
    if "goalkeeper" in position:
        return "Goalkeeper"
    if "back" in position:
        return "Defender"
    if "midfield" in position:
        return "Midfielder"
    if "wing" in position or "forward" in position or "striker" in position:
        return "Attacker"
    return "Hybrid"


def squad_phase(country, minutes):
    if country == "United States of America" and minutes >= 240:
        return "domestic regular"
    if country == "United States of America":
        return "domestic depth"
    if minutes >= 300:
        return "international regular"
    return "international review"


def init_feature_row(match, team_id, team_name, player):
    main_position = ""
    if player.get("positions"):
        main_position = max(
            player["positions"],
            key=lambda item: minutes_from_positions([item]),
        ).get("position", "")
    return {
        "match_id": match["match_id"],
        "match_date": match["match_date"],
        "player_id": player["player_id"],
        "player_name": player.get("player_nickname") or player["player_name"],
        "team_id": team_id,
        "team_name": team_name,
        "country": player.get("country", {}).get("name", "Unknown"),
        "position": main_position,
        "role": role_bucket(main_position),
        "minutes": minutes_from_positions(player.get("positions", [])),
        "shots": 0,
        "xg": 0.0,
        "goals": 0,
        "passes": 0,
        "progressive_passes": 0,
        "carries": 0,
        "progressive_carries": 0,
        "pressures": 0,
        "recoveries": 0,
        "interceptions": 0,
        "blocks": 0,
        "clearances": 0,
        "duels": 0,
        "dribbles": 0,
        "successful_dribbles": 0,
        "fouls_won": 0,
        "fouls_committed": 0,
        "turnovers": 0,
        "event_count": 0,
    }


def progressive_delta(event, action_key):
    start = event.get("location")
    end = event.get(action_key, {}).get("end_location")
    if not start or not end:
        return 0
    team = event.get("team", {}).get("name")
    direction = 1
    if team and team == event.get("possession_team", {}).get("name"):
        direction = 1
    return direction * (end[0] - start[0])


def add_event(row, event):
    event_type = event.get("type", {}).get("name")
    if event_type not in EVENT_TYPES:
        return
    row["event_count"] += 1
    if event_type == "Shot":
        row["shots"] += 1
        shot = event.get("shot", {})
        row["xg"] += float(shot.get("statsbomb_xg", 0))
        if shot.get("outcome", {}).get("name") == "Goal":
            row["goals"] += 1
    elif event_type == "Pass":
        row["passes"] += 1
        if progressive_delta(event, "pass") >= 10:
            row["progressive_passes"] += 1
    elif event_type == "Carry":
        row["carries"] += 1
        if progressive_delta(event, "carry") >= 8:
            row["progressive_carries"] += 1
    elif event_type == "Pressure":
        row["pressures"] += 1
    elif event_type == "Ball Recovery":
        row["recoveries"] += 1
    elif event_type == "Interception":
        row["interceptions"] += 1
    elif event_type == "Block":
        row["blocks"] += 1
    elif event_type == "Clearance":
        row["clearances"] += 1
    elif event_type == "Duel":
        row["duels"] += 1
    elif event_type == "Dribble":
        row["dribbles"] += 1
        if not event.get("dribble", {}).get("outcome", {}).get("name") == "Incomplete":
            row["successful_dribbles"] += 1
    elif event_type == "Foul Won":
        row["fouls_won"] += 1
    elif event_type in {"Foul Committed", "Dispossessed", "Miscontrol"}:
        row["turnovers"] += 1
        if event_type == "Foul Committed":
            row["fouls_committed"] += 1


def add_rates(row):
    minutes = max(row["minutes"], 1)
    for key in [
        "shots",
        "xg",
        "passes",
        "progressive_passes",
        "carries",
        "progressive_carries",
        "pressures",
        "recoveries",
        "duels",
        "turnovers",
    ]:
        row[f"{key}_p90"] = round(row[key] * 90 / minutes, 3)
    defensive = row["recoveries"] + row["interceptions"] + row["blocks"] + row["clearances"]
    row["defensive_actions"] = defensive
    row["defensive_actions_p90"] = round(defensive * 90 / minutes, 3)
    row["dribble_success_rate"] = round(
        row["successful_dribbles"] / row["dribbles"], 3
    ) if row["dribbles"] else 0.0
    row["contribution_index"] = round(
        row["xg_p90"] * 12
        + row["progressive_passes_p90"] * 0.7
        + row["progressive_carries_p90"] * 0.8
        + row["pressures_p90"] * 0.35
        + row["defensive_actions_p90"] * 0.65
        + row["dribble_success_rate"] * 2.4
        - row["turnovers_p90"] * 0.35,
        3,
    )
    return row


def build_player_match_features(root):
    matches = sorted(
        read_json(root / MATCH_PATH),
        key=lambda item: (item["match_date"], item["match_id"]),
    )
    rows = []
    match_rows = []
    for match in matches:
        match_id = match["match_id"]
        lineups = read_json(root / "data" / "lineups" / f"{match_id}.json")
        by_player = {}
        for team in lineups:
            for player in team["lineup"]:
                row = init_feature_row(match, team["team_id"], team["team_name"], player)
                if row["minutes"] > 0:
                    by_player[player["player_id"]] = row
        for event in read_json(root / "data" / "events" / f"{match_id}.json"):
            player = event.get("player")
            if not player or player["id"] not in by_player:
                continue
            add_event(by_player[player["id"]], event)
        for row in by_player.values():
            if row["event_count"] >= 3:
                rows.append(add_rates(row))
        match_rows.append(
            {
                "match_id": match_id,
                "match_date": match["match_date"],
                "home_team": match["home_team"]["home_team_name"],
                "away_team": match["away_team"]["away_team_name"],
                "home_score": match["home_score"],
                "away_score": match["away_score"],
                "event_rows": len(read_json(root / "data" / "events" / f"{match_id}.json")),
                "lineup_players": sum(len(team["lineup"]) for team in lineups),
            }
        )
    return rows, match_rows


def standardize(train_rows):
    means = {}
    stds = {}
    for col in FEATURE_COLUMNS:
        values = [float(row[col]) for row in train_rows]
        means[col] = statistics.mean(values)
        stds[col] = statistics.pstdev(values) or 1.0
    return means, stds


def vector(row, means, stds):
    return [(float(row[col]) - means[col]) / stds[col] for col in FEATURE_COLUMNS]


def sigmoid(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


def train_logistic(rows):
    train = [row for i, row in enumerate(rows) if i % 5 != 0]
    test = [row for i, row in enumerate(rows) if i % 5 == 0]
    means, stds = standardize(train)
    weights = [0.0] * len(FEATURE_COLUMNS)
    bias = 0.0
    lr = 0.045
    for _ in range(900):
        for row in train:
            x = vector(row, means, stds)
            pred = sigmoid(bias + sum(w * v for w, v in zip(weights, x)))
            error = pred - row["target"]
            bias -= lr * error
            for idx, value in enumerate(x):
                weights[idx] -= lr * error * value
    for row in rows:
        row["model_probability"] = sigmoid(
            bias + sum(w * v for w, v in zip(weights, vector(row, means, stds)))
        )
    metrics = evaluate(test, weights, bias, means, stds)
    importance = sorted(
        [
            {"feature": col, "weight": round(weight, 3), "direction": "positive" if weight >= 0 else "negative"}
            for col, weight in zip(FEATURE_COLUMNS, weights)
        ],
        key=lambda item: abs(item["weight"]),
        reverse=True,
    )
    return metrics, importance, {"weights": weights, "bias": bias, "means": means, "stds": stds}


def score_rows(rows, model):
    for row in rows:
        row["model_probability"] = sigmoid(
            model["bias"]
            + sum(
                weight * value
                for weight, value in zip(
                    model["weights"], vector(row, model["means"], model["stds"])
                )
            )
        )
        row.setdefault("future_contribution_index", "")
        row.setdefault("target", "")


def evaluate(test, weights, bias, means, stds):
    scored = []
    for row in test:
        pred = sigmoid(bias + sum(w * v for w, v in zip(weights, vector(row, means, stds))))
        scored.append((pred, row["target"]))
    if not scored:
        return {"rows": 0, "accuracy": 0, "precision": 0, "recall": 0, "brier": 0}
    tp = sum(1 for pred, target in scored if pred >= 0.5 and target == 1)
    tn = sum(1 for pred, target in scored if pred < 0.5 and target == 0)
    fp = sum(1 for pred, target in scored if pred >= 0.5 and target == 0)
    fn = sum(1 for pred, target in scored if pred < 0.5 and target == 1)
    brier = statistics.mean((pred - target) ** 2 for pred, target in scored)
    return {
        "rows": len(scored),
        "accuracy": round((tp + tn) / len(scored), 3),
        "precision": round(tp / (tp + fp), 3) if tp + fp else 0,
        "recall": round(tp / (tp + fn), 3) if tp + fn else 0,
        "brier": round(brier, 3),
        "positive_rate": round(sum(target for _, target in scored) / len(scored), 3),
    }


def attach_targets(rows):
    by_player = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item["player_id"], item["match_date"])):
        by_player[row["player_id"]].append(row)
    role_values = defaultdict(list)
    for row in rows:
        role_values[row["role"]].append(row["contribution_index"])
    role_medians = {
        role: statistics.median(values) for role, values in role_values.items()
    }
    modeled = []
    for player_rows in by_player.values():
        for idx, row in enumerate(player_rows):
            future = player_rows[idx + 1 :]
            if not future:
                continue
            next_impact = statistics.mean(item["contribution_index"] for item in future[:2])
            row["future_contribution_index"] = round(next_impact, 3)
            row["target"] = 1 if next_impact >= role_medians[row["role"]] else 0
            modeled.append(row)
    return modeled, role_medians


def summarize_players(rows):
    by_player = defaultdict(list)
    for row in rows:
        by_player[row["player_id"]].append(row)
    output = []
    for player_id, player_rows in by_player.items():
        minutes = sum(row["minutes"] for row in player_rows)
        if minutes < 80:
            continue
        latest = max(player_rows, key=lambda row: row["match_date"])
        total = defaultdict(float)
        for row in player_rows:
            for col in FEATURE_COLUMNS + ["contribution_index", "model_probability"]:
                total[col] += float(row[col]) * row["minutes"]
        weighted = {col: total[col] / minutes for col in FEATURE_COLUMNS + ["contribution_index", "model_probability"]}
        confidence = min(0.93, 0.52 + minutes / 600)
        data_risk = "low" if minutes >= 280 else "medium" if minutes >= 170 else "watch"
        review_priority = (
            weighted["model_probability"] * 62
            + weighted["contribution_index"] * 5.8
            + min(minutes, 360) / 18
            - weighted["turnovers_p90"] * 1.8
        )
        if latest["role"] == "Goalkeeper":
            review_priority *= 0.78
        action = "Scout video packet" if review_priority >= 88 else "Analyst review" if review_priority >= 74 else "Monitor sample"
        if data_risk == "watch":
            action = "Collect more minutes"
        output.append(
            {
                "player_id": player_id,
                "player_name": latest["player_name"],
                "team_name": latest["team_name"],
                "country": latest["country"],
                "role": latest["role"],
                "position": latest["position"],
                "squad_phase": squad_phase(latest["country"], minutes),
                "matches": len(player_rows),
                "minutes": round(minutes, 1),
                "review_priority": round(review_priority, 1),
                "model_probability": round(weighted["model_probability"], 3),
                "confidence": round(confidence, 3),
                "data_risk": data_risk,
                "next_action": action,
                "contribution_index": round(weighted["contribution_index"], 2),
                "shots_p90": round(weighted["shots_p90"], 2),
                "xg_p90": round(weighted["xg_p90"], 2),
                "progressive_passes_p90": round(weighted["progressive_passes_p90"], 2),
                "progressive_carries_p90": round(weighted["progressive_carries_p90"], 2),
                "pressures_p90": round(weighted["pressures_p90"], 2),
                "defensive_actions_p90": round(weighted["defensive_actions_p90"], 2),
                "turnovers_p90": round(weighted["turnovers_p90"], 2),
            }
        )
    output.sort(key=lambda row: row["review_priority"], reverse=True)
    return output


def build_data_quality(feature_rows, match_rows):
    total_rows = len(feature_rows)
    missing_position = sum(1 for row in feature_rows if not row["position"])
    low_minutes = sum(1 for row in feature_rows if row["minutes"] < 30)
    checks = [
        {
            "check_id": "DQ-001",
            "check": "Match event files loaded",
            "status": "Pass" if all(row["event_rows"] > 2500 for row in match_rows) else "Review",
            "result": f"{len(match_rows)} matches, {sum(row['event_rows'] for row in match_rows):,} event rows",
            "owner": "Data analyst",
        },
        {
            "check_id": "DQ-002",
            "check": "Lineup player coverage",
            "status": "Pass" if total_rows >= 120 else "Review",
            "result": f"{total_rows} player-match rows with event activity",
            "owner": "Football analytics",
        },
        {
            "check_id": "DQ-003",
            "check": "Position completeness",
            "status": "Pass" if missing_position / total_rows < 0.04 else "Review",
            "result": f"{pct(missing_position / total_rows)}% missing primary position",
            "owner": "Scouting ops",
        },
        {
            "check_id": "DQ-004",
            "check": "Small-sample review flag",
            "status": "Watch" if low_minutes else "Pass",
            "result": f"{low_minutes} player-match rows below 30 minutes",
            "owner": "Recruitment analyst",
        },
    ]
    return checks


def write_agentic_briefs(players):
    lines = ["# Agentic Scouting Briefs", ""]
    for idx, player in enumerate(players[:6], start=1):
        strengths = []
        if player["xg_p90"] >= 0.22:
            strengths.append("shot value")
        if player["progressive_passes_p90"] >= 4:
            strengths.append("progressive passing")
        if player["pressures_p90"] >= 14:
            strengths.append("pressing volume")
        if player["defensive_actions_p90"] >= 9:
            strengths.append("defensive activity")
        if not strengths:
            strengths.append("balanced contribution")
        lines.extend(
            [
                f"## {idx}. {player['player_name']}",
                "",
                f"- Role: {player['role']} for {player['team_name']}.",
                f"- Review priority: {player['review_priority']} with model probability {pct(player['model_probability'])}%.",
                f"- Why now: {', '.join(strengths)} with {player['minutes']:.0f} modeled minutes and {player['data_risk']} data risk.",
                f"- Suggested next step: {player['next_action']}.",
                "",
            ]
        )
    path = OUTPUT_DIR / "agentic_scouting_briefs.md"
    path.write_text("\n".join(lines))


def main():
    root = raw_root()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    feature_rows, match_rows = build_player_match_features(root)
    modeled_rows, role_medians = attach_targets(feature_rows)
    metrics, importance, model = train_logistic(modeled_rows)
    score_rows(feature_rows, model)
    players = summarize_players(feature_rows)
    data_quality = build_data_quality(feature_rows, match_rows)
    role_summary = []
    for role, rows in sorted(defaultdict(list, {
        role: [p for p in players if p["role"] == role] for role in {p["role"] for p in players}
    }).items()):
        role_summary.append(
            {
                "role": role,
                "players": len(rows),
                "avg_priority": round(statistics.mean(row["review_priority"] for row in rows), 1),
                "avg_model_probability": round(statistics.mean(row["model_probability"] for row in rows), 3),
            }
        )
    feature_fieldnames = [
        "match_id",
        "match_date",
        "player_id",
        "player_name",
        "team_name",
        "country",
        "position",
        "role",
        "minutes",
    ] + FEATURE_COLUMNS + ["contribution_index", "future_contribution_index", "target", "model_probability"]
    write_csv(ROOT / "data" / "player_match_features.csv", feature_rows, feature_fieldnames)
    player_fields = list(players[0].keys())
    write_csv(ROOT / "analysis" / "outputs" / "scouting_priority_queue.csv", players, player_fields)
    write_csv(ROOT / "data" / "match_manifest.csv", match_rows, list(match_rows[0].keys()))
    write_csv(ROOT / "analysis" / "outputs" / "data_quality_checks.csv", data_quality, list(data_quality[0].keys()))
    diagnostics = {
        "source": "StatsBomb Open Data MLS 2023",
        "competition_id": 44,
        "season_id": 107,
        "matches": len(match_rows),
        "event_rows": sum(row["event_rows"] for row in match_rows),
        "player_match_rows": len(feature_rows),
        "modeled_rows": len(modeled_rows),
        "player_shortlist_rows": len(players),
        "target_definition": "Next available appearance contribution index above role median.",
        "role_medians": {role: round(value, 3) for role, value in role_medians.items()},
        "holdout_metrics": metrics,
        "feature_importance": importance,
    }
    (OUTPUT_DIR / "model_diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
    app_payload = {
        "summary": {
            "matches": len(match_rows),
            "event_rows": sum(row["event_rows"] for row in match_rows),
            "modeled_rows": len(modeled_rows),
            "shortlist_players": len(players),
            "top_player": players[0]["player_name"],
            "top_priority": players[0]["review_priority"],
            "holdout_accuracy": metrics["accuracy"],
            "holdout_brier": metrics["brier"],
        },
        "players": players[:24],
        "feature_importance": importance,
        "model_metrics": metrics,
        "role_summary": role_summary,
        "data_quality": data_quality,
        "briefs": [
            {
                "player_name": player["player_name"],
                "role": player["role"],
                "brief": f"{player['player_name']} profiles as a {player['role'].lower()} review target with {pct(player['model_probability'])}% model probability, {player['contribution_index']} contribution index, and {player['data_risk']} data risk. Next action: {player['next_action']}."
            }
            for player in players[:6]
        ],
    }
    (OUTPUT_DIR / "app_payload.json").write_text(json.dumps(app_payload, indent=2))
    write_agentic_briefs(players)
    print(f"Wrote {len(players)} player shortlist rows from {len(match_rows)} public MLS matches.")
    print(f"Top review target: {players[0]['player_name']} at {players[0]['review_priority']} priority.")
    print(f"Holdout accuracy: {metrics['accuracy']} | Brier: {metrics['brier']}")


if __name__ == "__main__":
    main()
