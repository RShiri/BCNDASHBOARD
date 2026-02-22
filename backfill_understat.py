import os
import json
import re
import time
from selenium import webdriver

DATA_DIR = os.path.join('assets', 'data')
UNDERSTAT_URL = 'https://understat.com/team/Barcelona'

options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
driver.get(UNDERSTAT_URL)
time.sleep(5)
html = driver.page_source
driver.quit()

from bs4 import BeautifulSoup
import datetime

soup = BeautifulSoup(html, 'html.parser')
understat_matches = []
for container in soup.select('.calendar-date-container'):
    date_el = container.select_side = container.select_one('.calendar-date')
    if not date_el: continue
    
    match_info = container.select_one('.match-info[data-isresult="true"]')
    if not match_info: continue
    
    date_str = date_el.text.strip()
    try:
        dt = datetime.datetime.strptime(date_str, "%b %d, %Y")
        formatted_date = dt.strftime("%Y-%m-%d")
    except:
        continue
        
    xg_home_el = match_info.select_one('.teams-xG .team-home')
    xg_away_el = match_info.select_one('.teams-xG .team-away')
    
    if xg_home_el and xg_away_el:
        h_xg = xg_home_el.text.strip()
        a_xg = xg_away_el.text.strip()
        understat_matches.append({
            'datetime': formatted_date,
            'xG': {'h': h_xg, 'a': a_xg}
        })

print(f"Extracted {len(understat_matches)} matches from Understat DOM.")

count = 0
for f in os.listdir(DATA_DIR):
    if f.endswith('_cache.json'):
        path = os.path.join(DATA_DIR, f)
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        if 'understat' in data: continue
        
        ws_date_str = data.get('startTime')
        if not ws_date_str: continue
        ws_date = ws_date_str.split('T')[0]
        
        for um in understat_matches:
            if um.get('datetime', '').startswith(ws_date):
                data['understat'] = um
                with open(path, 'w', encoding='utf-8') as out:
                    json.dump(data, out, indent=4)
                count += 1
                print(f'Backfilled Understat for {f}')
                break
print(f'Backfilled {count} matches')
