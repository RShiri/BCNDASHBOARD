"""
Fetch match stats from Understat for match 29395 (Girona 2-1 Barcelona).
Reads all available fields directly from the match_info JSON blob.
"""

import urllib.request, re, json, math, os

UNDERSTAT_URL = "https://understat.com/match/29395"
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE    = os.path.join(_PROJECT_ROOT, "match_1914105_cache.json")


def _fetch_match_info():
    """Fetch and decode Understat match_info blob. Returns dict or None."""
    req = urllib.request.Request(
        UNDERSTAT_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            page = r.read().decode("utf-8")
    except Exception as e:
        print(f"  [Understat] Request failed: {e}")
        return None

    blobs = re.findall(r"var\s+(\w+)\s*=\s*JSON\.parse\('(.+?)'\);", page, re.DOTALL)
    for var_name, raw in blobs:
        try:
            decoded = raw.encode("utf-8").decode("unicode_escape")
            data = json.loads(decoded)
        except Exception:
            continue
        if "h_xg" in data:
            print(f"  [Understat/{var_name}] fetched OK")
            return data

    print("  [Understat] match_info not found")
    return None


def fetch_understat_stats():
    """
    Returns dict of all available Understat stats, or None on failure.
    Keys: h_xg, a_xg, h_shot, a_shot, h_shotOnTarget, a_shotOnTarget,
          h_goals, a_goals, h_deep, a_deep, h_ppda, a_ppda,
          team_h, team_a
    """
    info = _fetch_match_info()
    if info is None:
        return None
    return {
        "h_xg":           round(float(info.get("h_xg", 0)), 2),
        "a_xg":           round(float(info.get("a_xg", 0)), 2),
        "h_shot":         int(info.get("h_shot", 0)),
        "a_shot":         int(info.get("a_shot", 0)),
        "h_shotOnTarget": int(info.get("h_shotOnTarget", 0)),
        "a_shotOnTarget": int(info.get("a_shotOnTarget", 0)),
        "h_goals":        int(info.get("h_goals", 0)),
        "a_goals":        int(info.get("a_goals", 0)),
        "h_deep":         int(info.get("h_deep", 0)),
        "a_deep":         int(info.get("a_deep", 0)),
        "h_ppda":         round(float(info.get("h_ppda", 0)), 2),
        "a_ppda":         round(float(info.get("a_ppda", 0)), 2),
        "team_h":         info.get("team_h", "Home"),
        "team_a":         info.get("team_a", "Away"),
    }


def fetch_understat_xg():
    """Back-compat: returns (home_xg, away_xg) or (None, None)."""
    stats = fetch_understat_stats()
    if stats is None:
        return None, None
    return stats["h_xg"], stats["a_xg"]


def calc_ws_geometry_xg(cache_path):
    """Geometry-based xG from WhoScored coordinates. Returns (h_xg, a_xg, h_name, a_name)."""
    with open(cache_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    home_id = d["home"]["teamId"]
    away_id = d["away"]["teamId"]
    SHOT_TYPES = ("MissedShots", "SavedShot", "ShotOnPost", "Goal")

    def est(tid):
        total = 0.0
        for e in d.get("events", []):
            if e.get("teamId") != tid: continue
            if e.get("type", {}).get("displayName", "") not in SHOT_TYPES: continue
            x_sb = e.get("x", 0) * 1.20
            y_sb = 80 - e.get("y", 0) * 0.80
            dx = 120 - x_sb; dy = 40 - y_sb
            dist = max(math.sqrt(dx**2 + dy**2), 0.5)
            angle = math.atan2(4.0, dist)
            total += min(max((angle / (math.pi / 2)) * (1 / (1 + dist / 30)), 0.01), 0.95)
        return round(total, 2)

    return est(home_id), est(away_id), d["home"]["name"], d["away"]["name"]


def get_averaged_xg(cache_path=None):
    """Returns xG dict (Understat preferred, WS geometry fallback)."""
    if cache_path is None:
        cache_path = CACHE_FILE
    ws_home, ws_away, home_name, away_name = calc_ws_geometry_xg(cache_path)
    us_home, us_away = fetch_understat_xg()
    return {
        "home_xg":    us_home if us_home is not None else ws_home,
        "away_xg":    us_away if us_away is not None else ws_away,
        "home_name":  home_name,
        "away_name":  away_name,
        "source":     "Understat" if us_home is not None else "WhoScored geometry",
        "ws_home_xg": ws_home,
        "ws_away_xg": ws_away,
        "us_home_xg": us_home,
        "us_away_xg": us_away,
    }


if __name__ == "__main__":
    stats = fetch_understat_stats()
    if stats:
        print("\nAll Understat stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
