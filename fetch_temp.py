import cloudscraper
import re
import json

scraper = cloudscraper.create_scraper()
url = "https://www.whoscored.com/Matches/1968936/Live/Spain-Copa-del-Rey-2025-2026-Atletico-Madrid-Barcelona"

try:
    print(f"Fetching {url}...")
    html = scraper.get(url).text
    found = False
    for line in html.split("\n"):
        if "matchCentreData:" in line:
            found = True
            start_str = "matchCentreData:"
            start_idx = line.find(start_str) + len(start_str)
            content = line[start_idx:].strip()
            if "matchCentreEventTypeJson" in content:
                content = content.split("matchCentreEventTypeJson")[0].strip()
                if content.endswith(","): content = content[:-1]
            data = json.loads(content)
            with open("assets/data/match_1968936_cache.json", "w") as f:
                json.dump(data, f)
            print("Successfully extracted match data!", len(data["events"]), "events")
            break
            
    if not found:
        print("Data script not found. Cloudflare might be blocking us.")
        if "Cloudflare" in html:
            print("Confirmed Cloudflare block.")
        else:
            print("Response length:", len(html))
            
except Exception as e:
    print("Error:", e)
