
import cloudscraper
import json

scraper = cloudscraper.create_scraper()
# FC Barcelona ID = 8178
url = "https://www.fotmob.com/api/teams?id=8178&ccode3=ESP"

try:
    print(f"Fetching Team Data from {url}...")
    res = scraper.get(url)
    if res.status_code == 200:
        data = res.json()
        fixtures = data.get('fixtures', [])
        # Also check 'results' tab often in separate endpoint or tab
        # Actually in the main structure, 'fixtures' might only be future.
        # Check 'tabs' -> 'fixtures' -> 'all' ?
        
        # FotMob team fixtures usually require a separate call or deep parse.
        # Let's try matches/results endpoint:
        # https://www.fotmob.com/api/results?id=8178&season=2025/2026
        
    print("Trying results endpoint...")
    # This endpoint is guessed, but often works.
    url_results = "https://www.fotmob.com/api/results?id=8178"
    res = scraper.get(url_results)
    if res.status_code == 200:
        data = res.json()
        print("Results fetched.")
        # Traverse
        # usually data is grouped by league or month
        # Look for "Athletic Club" in January 2026
        
        def search_results(obj):
            if isinstance(obj, dict):
                if 'home' in obj and 'away' in obj:
                    h = obj['home']['name']
                    a = obj['away']['name']
                    date = obj.get('status', {}).get('utcTime', '')
                    tid = obj.get('id')
                    score = obj.get('status', {}).get('scoreStr', '?')
                    
                    if ('Barcelona' in h or 'Barcelona' in a) and ('Athletic' in h or 'Athletic' in a):
                        print(f"Match Candidate: ID {tid} | {h} vs {a} | {score} | {date}")
                        
                for k, v in obj.items():
                    search_results(v)
            elif isinstance(obj, list):
                for item in obj:
                    search_results(item)
                    
        search_results(data)
        
except Exception as e:
    print(f"Error: {e}")
