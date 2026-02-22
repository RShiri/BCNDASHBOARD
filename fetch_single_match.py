import os
import json
import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "assets", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options)
    return driver

def scrape_match(match_id):
    driver = setup_driver()
    url = f"https://www.whoscored.com/Matches/{match_id}/Live"
    print(f"Navigating to {url} with undetected-chromedriver...")
    driver.get(url)
    
    found = False
    for i in range(180):
        try:
            html = driver.page_source
            if "matchCentreData" in html:
                found = True
                break
        except Exception:
            pass
        time.sleep(1)
        if i % 10 == 0:
            print(f"Waiting for data or manual captcha solve... {i}s/180s")
            
    if found:
        soup = BeautifulSoup(html, 'html.parser')
        script_content = None
        for script in soup.find_all('script'):
            if script.string and 'matchCentreData:' in script.string:
                script_content = script.string
                break
                
        if script_content:
            print("Found data script. Parsing JSON...")
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
                
            print(f"Generated successfully. Events: {len(data.get('events', []))}")
        else:
            print("Failed to isolate script content.")
    else:
        print("Timeout waiting for matchCentreData script. Cloudflare may be blocking.")
        
    driver.quit()

if __name__ == "__main__":
    scrape_match("1968936")
