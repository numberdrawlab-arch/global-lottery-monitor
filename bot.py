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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

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
        f"ℹ️ **Status:** New winning array, PDF sheet, or asset link published!\n\n"
        f"🔗 **Direct Link:** {url}"
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

    print(f"🔄 Booting Bulletproof Monitoring Engine for {len(df)} entries...")
    session = requests.Session()

    for idx, row in df.iterrows():
        name = row['Lottery Name']
        region = row['Region/Country']
        url = row['Results Page URL']
        
        response_text = None
        max_retries = 3
        
        # Robust Retry Mechanism Loop
        for attempt in range(max_retries):
            try:
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Connection": "keep-alive"
                }
                
                response = session.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    response_text = response.text
                    break
                else:
                    print(f"⚠️ Retry {attempt + 1}/{max_retries} for {name} (Status: {response.status_code})")
                    time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} broken for {name}: {e}")
                time.sleep(random.uniform(2, 4))
        
        if not response_text:
            print(f"❌ Skipping {name}: Failed after {max_retries} structural connection attempts.")
            continue

        try:
            soup = BeautifulSoup(response_text, 'html.parser')
            
            # Remove high-churn layout decoration areas
            for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "header", "aside"]):
                tag.decompose()
                
            # Document Text Extraction
            core_text = soup.get_text()
            words = [word.strip() for word in core_text.split() if len(word.strip()) > 0]
            pure_text = " ".join(words)
            
            # Asset Attachment Extraction (PDFs, Images, Result Cards)
            asset_urls = []
            for link in soup.find_all(['a', 'img']):
                href = link.get('href') or link.get('src') or ''
                if any(ext in href.lower() for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.gif']):
                    asset_urls.append(href)
            
            combined_fingerprint = pure_text + " | Assets: " + " ".join(asset_urls)
            page_hash = hashlib.sha256(combined_fingerprint.encode('utf-8')).hexdigest()

            if name not in current_state:
                current_state[name] = page_hash
                updated = True
                print(f"✅ Initialized core data baseline for: {name}")
            elif current_state[name] != page_hash:
                send_notification(name, region, url)
                current_state[name] = page_hash
                updated = True
            
            time.sleep(random.uniform(1.0, 2.5))
            
        except Exception as parser_error:
            print(f"💥 Parsing distortion on structural processing for {name}: {parser_error}")
            continue

    if updated:
        save_state(current_state)
    print("🏁 Comprehensive global verification loop complete.")

if __name__ == "__main__":
    monitor_lotteries()
