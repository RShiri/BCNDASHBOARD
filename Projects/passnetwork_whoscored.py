"""
Barcelona vs Girona - Pass Network (WhoScored data source)
Date: February 16, 2026
Based on the exact logic from 4.11 Pass Networks.ipynb
"""

import math
import json
import time
import numpy as np
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.lines as mlines


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
WHOSCORED_MATCH_ID = 1914105
URL = (
    f"https://www.whoscored.com/Matches/{WHOSCORED_MATCH_ID}/Live/"
    "spain-laliga-2025-2026-girona-barcelona"
)
TEAM_NAME = "Barcelona"                  # as it appears in WhoScored data
OPPONENT  = "Girona"                     # opponent team

# Resolve paths relative to the project root (one level up from Projects/)
import os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
OUTPUT_IMG      = _os.path.join(_PROJECT_ROOT, "barcelona_girona_passnetwork_ws.png")
OUTPUT_IMG_OPP  = _os.path.join(_PROJECT_ROOT, "girona_barcelona_passnetwork_ws.png")
CACHE_FILE      = _os.path.join(_PROJECT_ROOT, "match_1914105_cache.json")

# WhoScored uses 0-100 coords; StatsBomb uses 0-120 x 0-80
SCALE_X = 1.20   # 100 -> 120
SCALE_Y = 0.80   # 100 -> 80


# ---------------------------------------------------------------------------
# STEP 1 - Scrape matchCentreData from WhoScored (Selenium)
# ---------------------------------------------------------------------------

def scrape_whoscored(url):
    """Open the WhoScored match page, return the parsed matchCentreData dict."""
    print("Initialising Chrome ...")
    opts = webdriver.ChromeOptions()
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=opts)
    try:
        print(f"Navigating to {url}")
        driver.get(url)

        print("Waiting 25 s for JS to render ...")
        time.sleep(25)

        html = driver.page_source
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")

    # Look for the <script> containing matchCentreData
    for script in soup.find_all("script"):
        text = script.string or ""
        if "matchCentreData:" in text:
            print("Found matchCentreData script block.")
            start = text.find("matchCentreData:") + len("matchCentreData:")
            content = text[start:].strip()

            # Trim at the next JS variable boundary
            if "matchCentreEventTypeJson" in content:
                content = content.split("matchCentreEventTypeJson")[0].strip()
                if content.endswith(","):
                    content = content[:-1]

            data = json.loads(content)
            n_events = len(data.get("events", []))
            print(f"Parsed OK - {n_events} events found.")
            return data

    # If we get here, dump for debug
    with open("who_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    raise RuntimeError(
        "matchCentreData not found in page source. "
        "Saved HTML to who_debug.html for inspection."
    )


# ---------------------------------------------------------------------------
# STEP 1b - Extract jersey numbers from matchCentreData
# ---------------------------------------------------------------------------

def extract_jersey_numbers(match_data, team_name):
    """
    Build a dict  { player_id: jersey_number }  from the WhoScored
    home / away player information block.
    """
    home = match_data.get("home", {})
    away = match_data.get("away", {})

    if team_name.lower() in home.get("name", "").lower():
        team_block = home
    elif team_name.lower() in away.get("name", "").lower():
        team_block = away
    else:
        return {}

    jersey_map = {}
    for player in team_block.get("players", []):
        pid = player.get("playerId")
        jn  = player.get("shirtNo")
        if pid is not None and jn is not None:
            jersey_map[pid] = int(jn)
    print(f"Jersey numbers found: {len(jersey_map)} players")
    return jersey_map


# ---------------------------------------------------------------------------
# STEP 2 - Convert WhoScored events to a DataFrame matching 4.11 format
# ---------------------------------------------------------------------------

def events_to_dataframe(match_data, team_name):
    """
    Convert the raw WhoScored events list into a pandas DataFrame that
    mirrors the columns the 4.11 notebook expects:
        id, type, player_id, team, x, y, minute, second, pass_outcome
    """
    # Identify Barcelona's teamId
    home = match_data.get("home", {})
    away = match_data.get("away", {})

    if team_name.lower() in home.get("name", "").lower():
        team_id = home["teamId"]
    elif team_name.lower() in away.get("name", "").lower():
        team_id = away["teamId"]
    else:
        raise ValueError(
            f"Team '{team_name}' not found. "
            f"Available: {home.get('name')}, {away.get('name')}"
        )

    rows = []
    for ev in match_data.get("events", []):
        evt_type = ev.get("type", {}).get("displayName", "")
        outcome  = ev.get("outcomeType", {}).get("displayName", "")
        ev_team  = ev.get("teamId")

        # Only keep events for our team
        if ev_team != team_id:
            continue

        rows.append({
            "id":           ev.get("id"),
            "type":         evt_type,
            "player_id":    ev.get("playerId"),
            "team":         team_name,
            "x":            ev.get("x", 0) * SCALE_X,
            "y":            80 - ev.get("y", 0) * SCALE_Y,   # flip Y axis
            "minute":       ev.get("minute", 0),
            "second":       ev.get("second", 0),
            # WhoScored marks successful passes with outcomeType "Successful"
            "pass_outcome": None if outcome == "Successful" else outcome,
        })

    df = pd.DataFrame(rows)
    print(f"DataFrame built: {len(df)} events for {team_name}")
    return df


# ---------------------------------------------------------------------------
# STEP 3 - Process passes (exact 4.11 notebook logic)
# ---------------------------------------------------------------------------

def process_passes(df):
    # Make a single column for time and sort chronologically
    df["newsecond"] = 60 * df["minute"] + df["second"]
    df = df.sort_values(by=["newsecond"]).reset_index(drop=True)

    # Identify passer and recipient (next action's player)
    df["passer"]    = df["player_id"]
    df["recipient"] = df["passer"].shift(-1)

    # Filter for passes, then successful passes
    passes_df = df.loc[df["type"] == "Pass"].copy()
    passes_df["pass_outcome"] = passes_df["pass_outcome"].fillna("Successful")
    completions = passes_df.loc[passes_df["pass_outcome"] == "Successful"]

    # Find the team's first substitution and filter passes before it
    sub_df    = df.loc[df["type"].isin(["SubstitutionOff", "SubstitutionOn"])]
    first_sub = sub_df["newsecond"].min()
    if pd.isna(first_sub) or first_sub <= (60 * 45):
        first_sub = 60 * 45

    completions = completions.loc[completions["newsecond"] < first_sub]

    # Average locations per passer
    average_locs_and_count = (
        completions.groupby("passer")
        .agg({"x": ["mean"], "y": ["mean", "count"]})
    )
    average_locs_and_count.columns = ["x", "y", "count"]

    # Passes between each passer-recipient pair
    passes_between = (
        completions.groupby(["passer", "recipient"])
        .id.count()
        .reset_index()
    )
    passes_between.rename(columns={"id": "pass_count"}, inplace=True)

    passes_between = passes_between.merge(
        average_locs_and_count, left_on="passer", right_index=True
    )
    passes_between = passes_between.merge(
        average_locs_and_count, left_on="recipient", right_index=True,
        suffixes=["", "_end"],
    )

    # Show only meaningful connections (>= 4 passes)
    passes_between = passes_between.loc[passes_between["pass_count"] >= 4]

    return average_locs_and_count, passes_between


# ---------------------------------------------------------------------------
# STEP 4 - Draw pass network (enhanced with jersey numbers & scaled lines)
# ---------------------------------------------------------------------------

# Line-width range: thinnest arrow = MIN_LW, thickest = MAX_LW
MIN_LW = 1.0
MAX_LW = 6.0


def pass_line_template(ax, x, y, end_x, end_y, line_color, lw=4):
    ax.annotate(
        "",
        xy=(end_y, end_x),
        xytext=(y, x),
        zorder=1,
        arrowprops=dict(
            arrowstyle="-|>", linewidth=lw, color=line_color, alpha=0.85
        ),
    )


def pass_line_template_shrink(ax, x, y, end_x, end_y, line_color,
                              lw=4, dist_delta=1.2):
    dist  = math.hypot(end_x - x, end_y - y)
    angle = math.atan2(end_y - y, end_x - x)
    upd_x = x + (dist - dist_delta) * math.cos(angle)
    upd_y = y + (dist - dist_delta) * math.sin(angle)
    pass_line_template(ax, x, y, upd_x, upd_y, line_color=line_color, lw=lw)


def draw_network(average_locs_and_count, passes_between,
                 jersey_map=None, title="", output_file="passnetwork.png"):
    pitch = VerticalPitch(pitch_type="statsbomb")
    fig, ax = pitch.draw(figsize=(10, 10))

    # --- Scale line widths by pass_count ---
    min_passes = passes_between["pass_count"].min()
    max_passes = passes_between["pass_count"].max()
    rng = max_passes - min_passes if max_passes != min_passes else 1

    for _, row in passes_between.iterrows():
        # Linear interpolation of line width
        lw = MIN_LW + (row["pass_count"] - min_passes) / rng * (MAX_LW - MIN_LW)
        pass_line_template_shrink(
            ax, row["x"], row["y"], row["x_end"], row["y_end"],
            "black", lw=lw,
        )

    # --- Player nodes ---
    pitch.scatter(
        average_locs_and_count.x,
        average_locs_and_count.y,
        s=500,
        color="#f0ece2",
        edgecolors="#010101",
        linewidth=2,
        alpha=1,
        ax=ax,
        zorder=2,
    )

    # --- Jersey numbers ---
    if jersey_map:
        for player_id, row in average_locs_and_count.iterrows():
            jn = jersey_map.get(int(player_id), "")
            if jn:
                pitch.annotate(
                    str(jn),
                    xy=(row.x, row.y),
                    c="#132743",
                    va="center",
                    ha="center",
                    size=10,
                    fontweight="bold",
                    ax=ax,
                    zorder=3,
                )

    # --- Legend for line boldness ---
    legend_counts = sorted(set([
        min_passes,
        int(np.percentile(passes_between["pass_count"], 25)),
        int(np.percentile(passes_between["pass_count"], 50)),
        int(np.percentile(passes_between["pass_count"], 75)),
        max_passes,
    ]))
    handles = []
    for cnt in legend_counts:
        lw = MIN_LW + (cnt - min_passes) / rng * (MAX_LW - MIN_LW)
        handles.append(
            mlines.Line2D([], [], color="black", linewidth=lw,
                          label=f"{cnt} passes", alpha=0.85)
        )
    ax.legend(
        handles=handles, loc="lower left", title="Pass frequency",
        fontsize=9, title_fontsize=10, framealpha=0.9,
    )

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"Saved: {_os.path.basename(output_file)}")
    plt.close(fig)



# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== WhoScored Pass Network ===")
    print(f"Match ID : {WHOSCORED_MATCH_ID}\n")

    # 1. Scrape (or load from cache)
    if _os.path.exists(CACHE_FILE):
        print("Loading cached data ...")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            match_data = json.load(f)
        print(f"Loaded {len(match_data.get('events', []))} events from cache.")
    else:
        match_data = scrape_whoscored(URL)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(match_data, f)
        print("Cached data to file.")

    # 2. Process BOTH teams
    for team, output_file in [(TEAM_NAME, OUTPUT_IMG), (OPPONENT, OUTPUT_IMG_OPP)]:
        print(f"\n--- {team} ---")

        jersey_map = extract_jersey_numbers(match_data, team)
        df = events_to_dataframe(match_data, team)
        avg_locs, pass_between = process_passes(df)

        draw_network(
            avg_locs,
            pass_between,
            jersey_map=jersey_map,
            title=f"{team} Pass Network - Girona vs Barcelona (16/02/2026)",
            output_file=output_file,
        )

    print("\nDone! Both pass networks saved.")
