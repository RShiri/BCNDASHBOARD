import urllib.request
import json
import re

url = "https://www.fotmob.com/api/matchDetails?matchId=5173360"

req = urllib.request.Request(
    url, 
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
)

try:
    response = urllib.request.urlopen(req).read()
    data = json.loads(response.decode('utf-8'))
    
    print("Match Name:", data.get("general", {}).get("matchName"))
    print("League:", data.get("general", {}).get("leagueName"))
    
    # Do they have shotmaps?
    content = data.get("content", {})
    shotmap = content.get("shotmap", {})
    if shotmap and shotmap.get("shots"):
        print(f"Found {len(shotmap.get('shots'))} shots!")
        print("First shot example:", list(shotmap.get("shots")[0].keys()))
    else:
        print("No shotmap found.")
        
    # Do they have pass networks?
    stats = content.get("stats", {})
    # Look for passing/possession data
    print("Stats keys available:", list(stats.keys()) if stats else "None")
    
    with open("fotmob_test.json", "w") as f:
        json.dump(data, f)
        
    print("Saved to fotmob_test.json to explore.")
except Exception as e:
    print("Error:", e)
