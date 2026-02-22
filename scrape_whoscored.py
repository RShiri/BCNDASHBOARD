

from selenium import webdriver
# import undetected_chromedriver as uc # Switch to standard
from bs4 import BeautifulSoup
import json
import time

URL = "https://www.whoscored.com/Matches/1848529/Live/Spain-Supercopa-de-Espana-2024-2025-Barcelona-Athletic-Club"
OUTPUT_FILE = "match_data.json"

try:
    print("Initializing Chrome (Standard)...")
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Try specific flags to avoid detection?
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=options)
    
    print(f"Navigating to {URL}...")
    driver.get(URL)
    
    print("Waiting for page load (20s)...")
    time.sleep(20) 
    
    print("Getting page source...")
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    print("Searching for matchCentreData...")
    script_content = None
    for script in soup.find_all('script'):
        if script.string and 'matchCentreData:' in script.string:
            script_content = script.string
            break
            
    if script_content:
        print("Found data script. Parsing JSON...")
        try:
             # Find start of JSON
             start_str = "matchCentreData:"
             start_idx = script_content.find(start_str) + len(start_str)
             
             # The end is usually marked by the next variable 'matchCentreEventTypeJson' or just a comma context
             # Let's count braces to extract valid JSON
             
             content = script_content[start_idx:].strip()
             
             # Heuristic: Read until the matching closing brace
             # Or use the split method from notebook
             # Notebook used: .split('matchCentreEventTypeJson')[0].strip()[:-1]
             
             if 'matchCentreEventTypeJson' in content:
                 json_str = content.split('matchCentreEventTypeJson')[0].strip()
                 if json_str.endswith(','): json_str = json_str[:-1]
             else:
                 # Fallback: naive brace counting
                 pass 
                 json_str = content # hope?
                 
             data = json.loads(json_str)
             print(f"Data parsed. Events count: {len(data.get('events', []))}")
             
             with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
             print(f"Saved to {OUTPUT_FILE}")
             
        except Exception as pe:
            print(f"JSON Parse Error: {pe}")
    else:
        print("matchCentreData script not found.")
        with open("who_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Dumped source to who_debug.html")

    driver.quit()

except Exception as e:
    print(f"Error: {e}")
