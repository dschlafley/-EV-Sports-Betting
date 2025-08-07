import streamlit as st
import pandas as pd
from pinnacle_scraper import scrape_pinnacle_props
from odds_api import get_all_player_props

def american_to_decimal(odds):
    try:
        odds = float(odds)
        return round((odds / 100) + 1, 4) if odds > 0 else round((100 / abs(odds)) + 1, 4)
    except:
        return None

def decimal_to_american(decimal):
    try:
        decimal = float(decimal)
        return f"+{round((decimal - 1) * 100)}" if decimal >= 2 else f"-{round(100 / (decimal - 1))}"
    except:
        return None

def implied_prob(decimal_odds):
    return 1 / decimal_odds if decimal_odds else None

def remove_vig(over_prob, under_prob):
    if over_prob and under_prob and (over_prob + under_prob) != 0:
        total = over_prob + under_prob
        return over_prob / total, under_prob / total
    return None, None

def calculate_ev(fair_prob, offered_odds):
    decimal = american_to_decimal(offered_odds)
    return round((decimal * fair_prob - 1) * 100, 2) if decimal and fair_prob else None

# Load Streamlit UI
st.title("MLB Player Prop +EV Dashboard")
st.caption("📊 Compares Pinnacle no-vig odds to sportsbook odds across multiple player prop markets")

# EV Threshold slider
ev_threshold = st.slider("Minimum EV% to display", min_value=0, max_value=50, value=5, step=1)

# Load Pinnacle props
with st.spinner("🔄 Scraping Pinnacle props..."):
    pinnacle_df = scrape_pinnacle_props()

# Load sportsbook odds
with st.spinner("🔄 Fetching sportsbook odds..."):
    book_df = get_all_player_props()

# Handle missing data
if pinnacle_df.empty or book_df.empty:
    st.warning("⚠️ No data found. Please check if props are live on Pinnacle and sportsbooks.")
    st.stop()

# Merge Pinnacle and sportsbook data by player and market
merged = pd.merge(book_df, pinnacle_df, on=["Player", "Market"], how="inner")

results = []

for _, row in merged.iterrows():
    try:
        pinnacle_over_decimal = american_to_decimal(row["Over_y"])
        pinnacle_under_decimal = american_to_decimal(row["Under_y"])
        best_odds = row["Over_x"]
        sportsbook = row["Book"]

        if not (pinnacle_over_decimal and pinnacle_under_decimal and best_odds):
            continue

        over_imp = implied_prob(pinnacle_over_decimal)
        under_imp = implied_prob(pinnacle_under_decimal)
        fair_over_prob, _ = remove_vig(over_imp, under_imp)
        ev = calculate_ev(fair_over_prob, best_odds)

        if ev is not None and ev > ev_threshold:
            fair_decimal_odds = 1 / fair_over_prob if fair_over_prob else None
            fair_american_odds = decimal_to_american(fair_decimal_odds) if fair_decimal_odds else None

            results.append({
                "Player": row["Player"],
                "Market": row["Market"],
                "Pinnacle True Odds": fair_american_odds,
                "Best Odds": int(best_odds),
                "Sportsbook": sportsbook,
                "EV%": ev
            })
    except Exception as e:
        print(f"⚠️ Error processing {row.get('Player', 'Unknown')}: {e}")
        continue

# Display results
if results:
    ev_df = pd.DataFrame(results).sort_values(by="EV%", ascending=False)
    st.success(f"✅ {len(ev_df)} +EV bets found (EV% > {ev_threshold}%)")
    st.dataframe(ev_df, use_container_width=True)
else:
    st.warning(f"🚫 No +EV bets found above {ev_threshold}%.")