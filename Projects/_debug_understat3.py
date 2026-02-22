import re
with open('understat_page.html', 'r', encoding='utf-8') as f: page = f.read()

print("vars:", re.findall(r"var\s+([A-Za-z0-9_]+)\s*=", page))
m = re.search(r"var\s+rostersData\s*=\s*JSON\.parse\('(.+?)'\);", page)
if m:
    print("Found rostersData!")
    import json
    data = json.loads(m.group(1).encode('utf-8').decode('unicode_escape'))
    print("Keys in rostersData:", list(data.keys()))
    if data.get('h'):
        first_player = list(data['h'].values())[0]
        print("First home player keys:", list(first_player.keys()))
        print("Shots:", first_player.get('shots'))
else:
    print("No rostersData found")
