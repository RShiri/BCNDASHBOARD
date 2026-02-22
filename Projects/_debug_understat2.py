import urllib.request, re

req = urllib.request.Request("https://understat.com/match/29395", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    page = r.read().decode("utf-8")

# Find just the shotsData definition
m = re.search(r"var\s+shotsData\s*=\s*JSON\.parse\('([^']+)'\)", page)
if m:
    print("Found shotsData!")
    # Decode it
    raw = m.group(1)
    # the hex escape decoding:
    import codecs, json
    decoded = codecs.decode(raw.replace('\\x', '%'), 'unicode_escape')
    data = json.loads(decoded)
    print("shotsData keys:", list(data.keys()))
    print("h length:", len(data.get("h", [])))
    print("a length:", len(data.get("a", [])))
    if data.get("h"):
        shot = data["h"][0]
        print("First home shot:")
        for k in ["minute", "xG", "player", "result"]:
            print(f"  {k}: {shot.get(k)}")
else:
    print("shotsData not found. Let's look for any 'JSON.parse'")
    for match in re.finditer(r"JSON\.parse", page):
        start = max(0, match.start() - 30)
        end = min(len(page), match.end() + 30)
        print("Context:", page[start:end])
