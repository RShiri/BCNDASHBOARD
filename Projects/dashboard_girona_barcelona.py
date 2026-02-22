"""
Match Dashboard Generator – Girona vs Barcelona (16/02/2026)
Single-page scrollable HTML with all sections visible.

Sections (top to bottom):
  1. Header + scoreline
  2. Match stats bars
  3. Combined shot map (both teams on one pitch, interactive Plotly)
  4. Pass Networks (side-by-side PNGs)
  5. Final Third Entries (side-by-side PNGs)
"""

import base64, json, math, os, sys

# Allow importing from same Projects/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from fetch_understat_xg import get_averaged_xg
    _HAS_UNDERSTAT = True
except ImportError:
    _HAS_UNDERSTAT = False

# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE    = os.path.join(_PROJECT_ROOT, "match_1914105_cache.json")
OUTPUT_HTML   = os.path.join(_PROJECT_ROOT, "girona_barcelona_dashboard.html")

IMGS = {
    "bcn_passnet": os.path.join(_PROJECT_ROOT, "assets", "1914105_away_passnetwork.png"),
    "gir_passnet": os.path.join(_PROJECT_ROOT, "assets", "1914105_home_passnetwork.png"),
    "bcn_final":   os.path.join(_PROJECT_ROOT, "assets", "1914105_away_final_third.png"),
    "gir_final":   os.path.join(_PROJECT_ROOT, "assets", "1914105_home_final_third.png"),
}
COMBINED_SHOTMAP    = os.path.join(_PROJECT_ROOT, "assets", "1914105_shotmap_ws.html")
COMBINED_SHOTMAP_WS = os.path.join(_PROJECT_ROOT, "assets", "1914105_shotmap_ws.html")

# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------
def load_stats():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    home = d.get("home", {}); away = d.get("away", {})
    events = d.get("events", [])
    hid = home.get("teamId");  aid = away.get("teamId")

    SH = ("MissedShots", "SavedShot", "ShotOnPost", "Goal")

    def count(tid, types):
        return sum(1 for e in events if e.get("teamId")==tid
                   and e.get("type",{}).get("displayName","") in types)

    def big(tid):
        return sum(1 for e in events if e.get("teamId")==tid
                   and e.get("type",{}).get("displayName","") in SH
                   and any(q.get("type",{}).get("displayName")=="BigChance"
                           for q in e.get("qualifiers",[])))

    # Possession from pass counts (WhoScored only source)
    hp = count(hid, ("Pass",)); ap = count(aid, ("Pass",))
    tot = hp + ap or 1

    # Pull all ground-truth stats from Understat
    us = None
    if _HAS_UNDERSTAT:
        try:
            from fetch_understat_xg import fetch_understat_stats
            us = fetch_understat_stats()
        except Exception as e:
            print(f"  [Understat] stats fetch failed: {e}")

    if us:
        # Use Understat values for all shot-related stats
        h_shots = us["h_shot"];           a_shots = us["a_shot"]
        h_on    = us["h_shotOnTarget"];   a_on    = us["a_shotOnTarget"]
        h_goals = us["h_goals"];          a_goals = us["a_goals"]
        h_xg    = us["h_xg"];             a_xg    = us["a_xg"]
        print(f"  [Understat] shots: Girona {h_shots} | Barcelona {a_shots}")
        print(f"  [Understat] SOT  : Girona {h_on}    | Barcelona {a_on}")
        print(f"  [Understat] xG   : Girona {h_xg}    | Barcelona {a_xg}")
    else:
        # Fallback to WhoScored event counts
        h_shots = count(hid, SH);           a_shots = count(aid, SH)
        h_on    = count(hid, ("SavedShot","Goal")); a_on = count(aid, ("SavedShot","Goal"))
        h_goals = count(hid, ("Goal",));     a_goals = count(aid, ("Goal",))
        h_xg    = 0.0;                       a_xg    = 0.0
        print("  [Fallback] Using WhoScored event counts")

    return {
        "home_name":   home.get("name", "Home"),
        "away_name":   away.get("name", "Away"),
        "home_goals":  h_goals,
        "away_goals":  a_goals,
        "home_shots":  h_shots,
        "away_shots":  a_shots,
        "home_on":     h_on,
        "away_on":     a_on,
        "home_bc":     big(hid),
        "away_bc":     big(aid),
        "home_xg":     h_xg,
        "away_xg":     a_xg,
        "home_passes": hp,
        "away_passes": ap,
        "home_poss":   round(100 * hp / tot),
        "away_poss":   round(100 * ap / tot),
    }

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def img_b64(path):
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def read_html(path):
    if not os.path.exists(path): return "<p>File not found</p>"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def extract_plotly_inline(path):
    """
    Extract the embeddable parts of a Plotly-generated HTML file:
    - The plotlyjs <script> CDN/inline include
    - The <div id="..."> container
    - The render <script> block
    Returns a string safe to inject directly into another HTML page.
    """
    import re
    if not os.path.exists(path):
        return "<p style='color:#888'>Shot map file not found.</p>"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    parts = []

    # 1. Plotly JS — capture the full inline <script> that has the Plotly source
    #    (Plotly writes it as a large inline block, not a CDN link)
    plotly_script = re.search(
        r'(<script type="text/javascript">window\.PlotlyConfig.*?</script>)',
        content, re.DOTALL
    )
    if plotly_script:
        parts.append(plotly_script.group(1))

    # Also grab any <script src="..." that references plotly
    for m in re.finditer(r'<script[^>]*src="[^"]*plotly[^"]*"[^>]*></script>', content):
        parts.append(m.group(0))

    # 2. The main plotly inline JS block (the huge one with all the data)
    plotly_data = re.search(
        r'(<script type="text/javascript">\s*window\.PlotlyConfig(?!.*window\.PlotlyConfig).*?</script>)',
        content, re.DOTALL
    )

    # Simpler approach: grab ALL scripts and all divs from <body>
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    if body_match:
        return body_match.group(1)

    return content  # fallback


def stat_row(hv, av, label):
    try:
        h = float(str(hv).replace("%",""))
        a = float(str(av).replace("%",""))
        t = h + a or 1
        hp = round(100*h/t); ap = 100-hp
    except:
        hp = ap = 50
    return f"""
      <div class="sr">
        <span class="sv home">{hv}</span>
        <div class="sb-wrap">
          <div class="sb"><div class="bh" style="width:{hp}%"></div><div class="ba" style="width:{ap}%"></div></div>
          <span class="sl">{label}</span>
        </div>
        <span class="sv away">{av}</span>
      </div>"""

# ---------------------------------------------------------------------------
# BUILD HTML
# ---------------------------------------------------------------------------
def build_html(stats, imgs, shotmap_ws_inline, shotmap_us_inline):
    H = stats["home_name"]   # Girona
    A = stats["away_name"]   # Barcelona
    HC = "#a50044"  # Girona red
    AC = "#004d98"  # Barcelona blue

    score = f"{stats['home_goals']} – {stats['away_goals']}"

    # Assign inline content for the two maps
    shotmap_ws = shotmap_ws_inline
    shotmap_us = shotmap_us_inline

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Match Dashboard – {H} vs {A}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#0d0d1a;color:#e0e0e0;}}

/* ── HEADER ── */
.hdr{{background:linear-gradient(135deg,#0d0d1a 0%,#1a1a3e 50%,#0d0d1a 100%);
  border-bottom:1px solid #2a2a5a;padding:32px 40px 24px;text-align:center}}
.match-label{{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#6666aa;margin-bottom:10px}}
.scoreline{{display:flex;align-items:center;justify-content:center;gap:28px;margin:12px 0}}
.tn{{font-size:26px;font-weight:900;letter-spacing:-0.5px}}
.tn.h{{color:{HC};text-shadow:0 0 30px {HC}55}}
.tn.a{{color:{AC};text-shadow:0 0 30px {AC}55}}
.sc{{font-size:52px;font-weight:900;color:#fff;letter-spacing:-2px;text-shadow:0 0 40px #ffffff33}}
.badge{{display:inline-block;background:#1e1e4a;border:1px solid #3a3a7a;border-radius:20px;
  padding:4px 18px;font-size:12px;color:#9999cc;margin-top:8px}}

/* ── STATS ── */
.stats-section{{background:#111128;border-bottom:1px solid #222244;padding:28px 0;}}
.inner{{max-width:860px;margin:0 auto;padding:0 20px}}
.stitle{{text-align:center;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#6666aa;margin-bottom:20px}}
.sr{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.sv{{font-size:15px;font-weight:700;width:60px;text-align:center}}
.sv.home{{color:{HC}}} .sv.away{{color:{AC}}}
.sb-wrap{{flex:1;text-align:center}}
.sb{{display:flex;height:6px;border-radius:3px;overflow:hidden;background:#1a1a3a;margin-bottom:5px}}
.bh{{background:{HC};transition:width .5s}} .ba{{background:{AC};transition:width .5s}}
.sl{{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#8888bb}}

/* ── SECTIONS ── */
.section{{padding:40px 20px}}
.section+.section{{border-top:1px solid #1a1a3a}}
.sec-header{{text-align:center;margin-bottom:28px}}
.sec-header h2{{font-size:22px;font-weight:700;color:#ccccee;letter-spacing:-0.3px}}
.sec-header p{{font-size:12px;color:#8888bb;margin-top:6px}}

/* ── DUAL SHOTMAP ── */
.shotmap-dual{{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:1500px;margin:0 auto;}}
.shotmap-panel{{border-radius:12px;overflow:hidden;border:1px solid #222244;
  background:#1a1a2e;padding:8px 0;}}
.shotmap-panel h4{{text-align:center;margin:6px 0 2px;font-size:13px;letter-spacing:.05em;color:#aaaacc;}}
.shotmap-panel>div{{width:100% !important;}}
.js-plotly-plot,.plot-container{{width:100% !important;}}

/* ── TWO-COL ── */
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:24px;max-width:1300px;margin:0 auto}}
@media(max-width:900px){{.two-col{{grid-template-columns:1fr}}}}

/* ── CARDS ── */
.card{{background:#111128;border:1px solid #222244;border-radius:12px;overflow:hidden;
  transition:border-color .2s,box-shadow .2s}}
.card:hover{{border-color:#4444aa;box-shadow:0 4px 30px #0000aa22}}
.card-header{{padding:14px 20px;border-bottom:1px solid #222244;display:flex;align-items:center;gap:10px}}
.dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.card-header h3{{font-size:13px;font-weight:600;letter-spacing:.5px;color:#ccccee}}
.card img{{width:100%;display:block}}

/* ── FOOTER ── */
.footer{{text-align:center;padding:20px;font-size:11px;color:#444466;border-top:1px solid #1a1a2e}}
</style>
</head>
<body>

<!-- ══ HEADER ══ -->
<div class="hdr">
  <div class="match-label">La Liga 2025/26  ·  Match Dashboard</div>
  <div class="scoreline">
    <div class="tn h">{H}</div>
    <div class="sc">{score}</div>
    <div class="tn a">{A}</div>
  </div>
  <div class="badge">📅 16 February 2026  ·  WhoScored Data</div>
</div>

<!-- ══ STATS ══ -->
<div class="stats-section">
  <div class="inner">
    <div class="stitle">Match Statistics</div>
    {stat_row(stats['home_shots'],  stats['away_shots'],  'Total Shots')}
    {stat_row(stats['home_on'],     stats['away_on'],     'Shots on Target')}
    {stat_row(stats['home_bc'],     stats['away_bc'],     'Big Chances')}
    {stat_row(stats['home_xg'],     stats['away_xg'],     'xG (est.)')}
    {stat_row(stats['home_passes'], stats['away_passes'], 'Passes')}
    {stat_row(str(stats['home_poss'])+'%', str(stats['away_poss'])+'%', 'Possession')}
  </div>
</div>

<!-- == SHOT MAPS == -->
<div class="section">
  <div class="sec-header">
    <h2>&#127919; Shot Maps</h2>
    <p>
      <span style="color:{HC};font-weight:700">{H}</span> attacking &#8594;&nbsp;&nbsp;|
      &nbsp;&nbsp;<span style="color:{AC};font-weight:700">{A}</span> attacking &#8592;
      &nbsp;&middot;&nbsp; Dot size = xG &nbsp;&middot;&nbsp; &#11088; = Big Chance / Penalty &nbsp;&middot;&nbsp; Hover for details
    </p>
  </div>
  <div class="shotmap-dual">
    <div class="shotmap-panel">
      <h4>&#128200; WhoScored xG Model</h4>
      {shotmap_ws}
    </div>
    <div class="shotmap-panel">
      <h4>&#127775; Understat xG Model</h4>
      {shotmap_us}
    </div>
  </div>
</div>

<!-- ══ PASS NETWORKS ══ -->
<div class="section">
  <div class="sec-header">
    <h2>🔗 Pass Networks</h2>
    <p>Average player positions · Line thickness = pass volume between pairs · First 11 before first sub</p>
  </div>
  <div class="two-col">
    <div class="card">
      <div class="card-header">
        <div class="dot" style="background:{HC}"></div>
        <h3>{H} Pass Network</h3>
      </div>
      <img src="{imgs['gir_passnet']}" alt="{H} pass network" loading="lazy">
    </div>
    <div class="card">
      <div class="card-header">
        <div class="dot" style="background:{AC}"></div>
        <h3>{A} Pass Network</h3>
      </div>
      <img src="{imgs['bcn_passnet']}" alt="{A} pass network" loading="lazy">
    </div>
  </div>
</div>

<!-- ══ FINAL THIRD ══ -->
<div class="section">
  <div class="sec-header">
    <h2>⚡ Final Third Entries</h2>
    <p>Passes originating outside the final third with destination inside · Green = Complete · Red = Incomplete</p>
  </div>
  <div class="two-col">
    <div class="card">
      <div class="card-header">
        <div class="dot" style="background:{HC}"></div>
        <h3>{H} Final Third Entries</h3>
      </div>
      <img src="{imgs['gir_final']}" alt="{H} final third" loading="lazy">
    </div>
    <div class="card">
      <div class="card-header">
        <div class="dot" style="background:{AC}"></div>
        <h3>{A} Final Third Entries</h3>
      </div>
      <img src="{imgs['bcn_final']}" alt="{A} final third" loading="lazy">
    </div>
  </div>
</div>

<div class="footer">Data: WhoScored · Match #1914105 · BCNProject Analytics</div>

</body>
</html>"""

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Match Dashboard Generator ===\n")

    stats = load_stats()
    print(f"  {stats['home_name']} {stats['home_goals']} - {stats['away_goals']} {stats['away_name']}")

    print("Embedding images...")
    imgs = {k: img_b64(v) for k, v in IMGS.items()}
    for k, v in imgs.items():
        print(f"  {k}: {'OK ' + str(len(v)//1024) + 'KB' if v else 'MISSING'}")

    print("Loading shot maps...")
    sm_ws = extract_plotly_inline(COMBINED_SHOTMAP_WS)
    sm_us = extract_plotly_inline(COMBINED_SHOTMAP)
    print(f"  WhoScored map body: {len(sm_ws)//1024}KB")
    print(f"  Understat map body: {len(sm_us)//1024}KB")

    print("Building dashboard HTML...")
    html = build_html(stats, imgs, sm_ws, sm_us)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = os.path.getsize(OUTPUT_HTML) / 1024 / 1024
    print(f"\nDONE: {os.path.basename(OUTPUT_HTML)} ({size_mb:.1f} MB)")
