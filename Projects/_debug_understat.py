import urllib.request, re, json

req = urllib.request.Request("https://understat.com/match/29395", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    page = r.read().decode("utf-8")

m = re.search(r"var shotsData\s*=\s*JSON\.parse\('([^']+)'\);", page)
if m:
    raw = m.group(1)
    decoded = raw.encode('utf-8').decode('unicode_escape')
    data = json.loads(decoded)
    print("shotsData keys:", list(data.keys()))
    print("home shots count:", len(data.get("h", [])))
    print("away shots count:", len(data.get("a", [])))
    if data.get("h"):
        print("first home shot xG:", data["h"][0].get('xG'))
else:
    print('var shotsData not found')
