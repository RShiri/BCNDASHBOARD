import os
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "assets", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# URL for Barcelona 2025/26 Fixtures. Since 25/26 might not be listed fully yet, we point to the main tracking page.
# Using standard team fixtures view
TEAM_FIXTURES_URL = "https://www.whoscored.com/Teams/65/Fixtures/Spain-Barcelona"

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    # Uncomment to run headless if preferred (may increase Cloudflare detection risk)
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extract_match_data(driver, url, match_id):
    print(f"Navigating to {url}...")
    driver.get(url)
    
    # Random organic wait
    time.sleep(15)
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    script_content = None
    for script in soup.find_all('script'):
        if script.string and 'matchCentreData:' in script.string:
            script_content = script.string
            break
            
    if script_content:
        print(f"[{match_id}] Found data script. Parsing JSON...")
        try:
            start_str = "matchCentreData:"
            start_idx = script_content.find(start_str) + len(start_str)
            content = script_content[start_idx:].strip()
            
            if 'matchCentreEventTypeJson' in content:
                json_str = content.split('matchCentreEventTypeJson')[0].strip()
                if json_str.endswith(','): json_str = json_str[:-1]
            else:
                json_str = content
                
            data = json.loads(json_str)
            
            output_file = os.path.join(DATA_DIR, f"match_{match_id}_cache.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
            print(f"[{match_id}] Generated successfully. Events: {len(data.get('events', []))}")
            return True
            
        except Exception as pe:
            print(f"[{match_id}] JSON Parse Error: {pe}")
            return False
    else:
        print(f"[{match_id}] matchCentreData script not found. Likely blocked by Cloudflare or no data available yet.")
        return False


import os
import json
import time
import re
import urllib.request
import subprocess
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

FIXTURES_URL = "https://www.whoscored.com/teams/65/fixtures/spain-barcelona"
UNDERSTAT_URL = "https://understat.com/team/Barcelona/2025"

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def fetch_understat_team_data():
    """Fetches all Barcelona matches from Understat for cross-referencing xG."""
    print("Fetching Understat season data...")
    req = urllib.request.Request(UNDERSTAT_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        m = re.search(r"var datesData\s*=\s*JSON\.parse\('(.+?)'\);", html)
        if m:
            data = json.loads(m.group(1).encode('utf-8').decode('unicode_escape'))
            return [d for d in data if d.get('isResult') == True]
    except Exception as e:
        print(f"Failed to fetch Understat data: {e}")
    return []

def match_understat_data(ws_date_str, understat_matches):
    """Fuzzy link a WhoScored match to an Understat match by Date."""
    if not ws_date_str or not understat_matches: return None
    try:
        ws_date = ws_date_str.split('T')[0]
        for um in understat_matches:
            if um.get('datetime', '').startswith(ws_date):
                return um
    except Exception:
        pass
    return None

def extract_match_data(driver, url, match_id, understat_matches):
    print(f"Navigating to {url}...")
    driver.get(url)
    time.sleep(15)
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    script_content = None
    for script in soup.find_all('script'):
        if script.string and 'matchCentreData:' in script.string:
            script_content = script.string
            break
            
    if script_content:
        print(f"[{match_id}] Found data script. Parsing JSON...")
        try:
            start_str = "matchCentreData:"
            start_idx = script_content.find(start_str) + len(start_str)
            content = script_content[start_idx:].strip()
            if 'matchCentreEventTypeJson' in content:
                json_str = content.split('matchCentreEventTypeJson')[0].strip()
                if json_str.endswith(','): json_str = json_str[:-1]
            else:
                json_str = content
                
            data = json.loads(json_str)
            
            # Cross-reference Understat
            ws_date = data.get("startTime")
            us_match = match_understat_data(ws_date, understat_matches)
            if us_match:
                print(f"[{match_id}] Matched Understat game! Home xG: {us_match['xG']['h']}, Away xG: {us_match['xG']['a']}")
                data["understat"] = us_match
            
            output_file = os.path.join(DATA_DIR, f"match_{match_id}_cache.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
            print(f"[{match_id}] Cached successfully. Events: {len(data.get('events', []))}")
            return True
            
        except Exception as pe:
            print(f"[{match_id}] JSON Parse Error: {pe}")
            return False
    else:
        print(f"[{match_id}] matchCentreData not found. Not played yet or blocked.")
        return False

def trigger_data_pipeline():
    """Run the ETL pipeline (DB Parser + Asset Generator)"""
    print(">>> Triggering DB Parser...")
    subprocess.run(["python", os.path.join(PROJECT_ROOT, "EliteAnalytics", "backend", "parser.py")])
    print(">>> Triggering Asset Generator...")
    subprocess.run(["python", os.path.join(PROJECT_ROOT, "generate_all_assets.py")])
    print(">>> Pipeline Complete!")

def run_scraper_cycle():
    print(f"\n[{datetime.datetime.now()}] Starting Scraper Cycle...")
    driver = setup_driver()
    new_match_found = False
    
    try:
        understat_matches = fetch_understat_team_data()
        match_ids = ["1968936"]
            
        print(f"Targeting {len(match_ids)} fixture links.")
        
        for match_id in match_ids:
            if os.path.exists(os.path.join(DATA_DIR, f"match_{match_id}_cache.json")):
                continue
                
            url = f"https://www.whoscored.com/Matches/{match_id}/Live"
            if extract_match_data(driver, url, match_id, understat_matches):
                new_match_found = True
                
            time.sleep(15) # Wait between requests to avoid bans
            
    except Exception as e:
        print(f"Cycle error: {e}")
    finally:
        driver.quit()
        
    if new_match_found:
        trigger_data_pipeline()
    else:
        print("No new matches processed.")

def main():
    print("Elite Scraper Daemon Started. Will check for new matches periodically.")
    while True:
        run_scraper_cycle()
        print("Sleeping for 60 minutes before next check...")
        time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    main()
