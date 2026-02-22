from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import re
import time

def get_barca_match_ids():
    url = "https://www.whoscored.com/teams/65/fixtures/spain-barcelona"
    
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    print(f"Connecting to {url}...")
    
    try:
        driver.get(url)
        time.sleep(5) 
        # Find the div that actually contains the team fixtures
        time.sleep(5)
        
        # Get elements only within the fixtures table
        fixture_links = driver.find_elements(By.CSS_SELECTOR, "#team-fixtures .result a")
        if not fixture_links:
            fixture_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/Matches/']")
            
        match_ids = []
        for el in fixture_links:
            href = el.get_attribute("href")
            if href and "/matches/" in href.lower():
                m = re.search(r'(?i)/matches/(\d+)/live', href)
                if m:
                    match_ids.append(m.group(1))
        
        unique_ids = list(dict.fromkeys(match_ids))
        print(f"Found {len(unique_ids)} Match IDs:")
        for m_id in unique_ids:
            print(m_id)
            
        return unique_ids
    
    finally:
        driver.quit()

if __name__ == "__main__":
    ids = get_barca_match_ids()
