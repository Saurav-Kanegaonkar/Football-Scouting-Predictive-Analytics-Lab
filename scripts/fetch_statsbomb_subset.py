import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "statsbomb-open-data"
BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master"


def download(path):
    destination = RAW_ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    url = f"{BASE_URL}/{path}"
    print(f"Fetching {path}")
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())


def main():
    download("data/competitions.json")
    download("data/matches/44/107.json")
    matches = json.loads((RAW_ROOT / "data" / "matches" / "44" / "107.json").read_text())
    for match in matches:
        match_id = match["match_id"]
        download(f"data/events/{match_id}.json")
        download(f"data/lineups/{match_id}.json")
    print(f"StatsBomb MLS subset ready at {RAW_ROOT}")


if __name__ == "__main__":
    main()
