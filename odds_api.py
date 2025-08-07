import requests
import datetime
import pandas as pd

API_KEY = "52ed43bdddaa70b7cb537ced175df0aa"
BASE_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/events"
HEADERS = {"User-Agent": "Mozilla/5.0"}

SUPPORTED_BOOKS = [
    "fanduel", "draftkings", "betmgm", "caesars", "pointsbetus", "betrivers", "wynnbet", "barstool"
]

MARKET_KEYS = {
    "batter_home_runs": "Home Runs",
    "batter_total_bases": "Total Bases",
    "pitcher_strikeouts": "Strikeouts",
    "pitcher_outs": "Pitching Outs",
    "pitcher_earned_runs": "Earned Runs"
}

def get_today_event_ids():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.date()

    url = f"{BASE_URL}?apiKey={API_KEY}&dateFormat=iso&regions=us"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"❌ Failed to fetch events: {response.status_code}")
        return []

    events = response.json()
    mlb_event_ids = []

    print(f"📅 Found {len(events)} MLB events for {today}")
    for event in events:
        try:
            commence_time = datetime.datetime.fromisoformat(event['commence_time']).replace(tzinfo=datetime.timezone.utc)
            if commence_time.date() == today and commence_time > now_utc:
                mlb_event_ids.append(event["id"])
        except Exception as e:
            print(f"⚠️ Error parsing event time: {e}")

    print(f"🕒 {len(mlb_event_ids)} games remaining (excluding live/in-progress games)")
    return mlb_event_ids


def get_all_player_props():
    all_props = []
    event_ids = get_today_event_ids()

    for event_id in event_ids:
        url = f"{BASE_URL}/{event_id}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": ",".join(MARKET_KEYS.keys()),
            "oddsFormat": "american"
        }

        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"⚠️ Error fetching event {event_id}: {response.status_code}")
            continue

        data = response.json()
        for bookmaker in data.get("bookmakers", []):
            book = bookmaker.get("key")
            if book not in SUPPORTED_BOOKS:
                continue

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                market_label = MARKET_KEYS.get(market_key)

                if not market_label:
                    continue

                for outcome in market.get("outcomes", []):
                    # For batter markets, only keep standard 0.5 lines
                    if outcome.get("point") != 0.5 and market_key.startswith("batter_"):
                        continue

                    player = outcome.get("description")
                    odds = outcome.get("price")
                    label = outcome.get("name").lower()

                    if not player or odds is None or label not in ["over", "under"]:
                        continue

                    # Check if this player+market+book already exists
                    existing = next((item for item in all_props if
                                     item["Player"] == player and
                                     item["Market"] == market_label and
                                     item["Book"] == book), None)

                    if existing:
                        existing["Over" if label == "over" else "Under"] = odds
                    else:
                        all_props.append({
                            "Player": player,
                            "Market": market_label,
                            "Book": book,
                            "Over": odds if label == "over" else None,
                            "Under": odds if label == "under" else None
                        })

    return pd.DataFrame(all_props)


# For testing
if __name__ == "__main__":
    df = get_all_player_props()
    if not df.empty:
        print(df)
    else:
        print("⚠️ No props found.")