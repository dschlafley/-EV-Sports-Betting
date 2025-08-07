import time
import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROMEDRIVER_PATH = "C:\\Users\\Dane Schlafley\\OneDrive\\Documents\\EV Betting App\\chromedriver.exe"

MARKET_NAME_MAP = {
    "homeruns": "Home Runs",
    "totalbases": "Total Bases",
    "earnedruns": "Earned Runs",
    "hitsallowed": "Hits Allowed",
    "strikeouts": "Strikeouts",
    "pitchingouts": "Pitching Outs"
}

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=chrome_options)

def get_game_links(driver):
    driver.get("https://www.pinnacle.com/en/baseball/matchups/")
    print("🔍 Navigating to Pinnacle MLB matchups page...")
    time.sleep(4)

    links = []
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/en/baseball/mlb/']"))
        )
        anchor_tags = driver.find_elements(By.CSS_SELECTOR, "a[href*='/en/baseball/mlb/']")
        for a in anchor_tags:
            href = a.get_attribute("href")
            if "/en/baseball/mlb/" in href and "/matchups/" not in href:
                clean_url = href.split("#")[0]
                if clean_url not in links:
                    links.append(clean_url)
        print(f"🔗 Found {len(links)} valid game links.")
    except Exception as e:
        print(f"⚠️ Could not load matchup links: {e}")

    return links

def click_show_all(driver):
    try:
        show_all_button = WebDriverWait(driver, 4).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Show All')]"))
        )
        show_all_button.click()
        time.sleep(2)
    except (TimeoutException, ElementClickInterceptedException):
        pass

def decimal_to_american(decimal_str):
    try:
        decimal = float(decimal_str)
        if decimal >= 2.0:
            return f"+{round((decimal - 1) * 100):.0f}"
        else:
            return f"-{round(100 / (decimal - 1)):.0f}"
    except:
        return decimal_str

def normalize_market(raw_text):
    # Extract between parentheses
    matches = re.findall(r"\((.*?)\)", raw_text)
    for m in matches:
        cleaned = re.sub(r"[^a-zA-Z]", "", m).lower()
        if cleaned in MARKET_NAME_MAP:
            return MARKET_NAME_MAP[cleaned]
    return None

def extract_props(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    data = []

    player_sections = soup.find_all("span", class_="titleText-BgvECQYfHf")
    for section in player_sections:
        raw_text = section.get_text()
        market = normalize_market(raw_text)
        if not market:
            continue

        player_name = raw_text.split("(")[0].strip()
        parent_div = section.find_parent("div")
        if not parent_div:
            continue

        sibling_rows = parent_div.find_all_next("div", class_=lambda x: x and "row" in x.lower())
        for row in sibling_rows:
            text = row.get_text().lower()
            if "over" in text and "under" in text:
                try:
                    odds_spans = row.find_all("span", class_=lambda x: x and "price" in x.lower())
                    if len(odds_spans) >= 2:
                        over_odds = decimal_to_american(odds_spans[0].text.strip())
                        under_odds = decimal_to_american(odds_spans[1].text.strip())

                        data.append({
                            "Player": player_name,
                            "Market": market,
                            "Over": over_odds,
                            "Under": under_odds
                        })
                        break
                except:
                    continue

    return data

def scrape_pinnacle_props():
    driver = setup_driver()
    all_data = []

    try:
        links = get_game_links(driver)
        for link in links:
            print(f"➡️ Visiting: {link}")
            try:
                driver.get(link)
                time.sleep(4)
                click_show_all(driver)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                game_data = extract_props(driver)
                all_data.extend(game_data)
            except Exception as e:
                print(f"⚠️ Error visiting {link}: {e}")
    finally:
        driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        print(f"✅ Scraped {len(df)} player props.")
        print(df)
        return df
    else:
        print("❌ No player props found.")
        return pd.DataFrame()

if __name__ == "__main__":
    scrape_pinnacle_props()