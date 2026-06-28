import os
import json
import time
import hashlib
import requests
import random
import pandas as pd
from bs4 import BeautifulSoup

CSV_PATH = "worldwide_registered_lotteries_direct_results_verified.csv"
STATE_FILE = "lottery_state_tracker.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Enhanced headers to blend in as a real desktop browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_notification(lottery_name, region, url):
    message = (
        f"🚨 **NEW LOTTERY RESULT DETECTED** 🚨\n\n"
        f"🏆 **Lottery:** {lottery_name}\n"
        f"🌍 **Region:** {region}\n"
        f"ℹ️ **Status:** New drawing numbers published!\n\n"
        f"🔗 **Direct Results Link:** {url}"
    )
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        tele_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(tele_url, json=payload, timeout=10)
        except Exception as e:
            print(f"❌ Telegram alert failed for {lottery_name}: {e}")
    print(f"📡 Notification sent for {lottery_name} ({region})")

def monitor_lotteries():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: Could not find {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    current_state = load_state()
    updated = False

    print(f"🔄 Checking {len(df)} lottery endpoints for live updates...")

    for idx, row in df.iterrows():
        name = row['Lottery Name']
        region = row['Region/Country']
        url = row['Results Page URL']
        
        try:
            # Added a modern timeout and browser mimicry configuration
            response = requests.get(url, headers=HEADERS, timeout=20)
            
            if response.status_code != 200:
                print(f"⚠️ Skipped {name}: Received Status Code {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Clean page elements that change constantly on every load
            for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
                tag.decompose()
                
            core_text = soup.get_text()
            # Clean up excessive spaces and blanks
            clean_text = " ".join(core_text.split())
            page_hash = hashlib.sha256(clean_text.encode('utf-8')).hexdigest()

            if name not in current_state:
                current_state[name] = page_hash
                updated = True
                print(f"✅ Initialized state tracking for: {name}")
            elif current_state[name] != page_hash:
                send_notification(name, region, url)
                current_state[name] = page_hash
                updated = True
            
            # Use random pacing to stop firewalls from pattern-blocking us
            time.sleep(random.uniform(1.0, 2.5))
            
        except Exception as e:
            print(f"💥 Connection issue with {name}: {e}")
            continue

    if updated:
        save_state(current_state)
    print("🏁 Execution complete.")

if __name__ == "__main__":
    monitor_lotteries()
