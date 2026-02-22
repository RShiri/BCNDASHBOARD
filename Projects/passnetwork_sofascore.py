"""
Barcelona vs Girona - Pass Network (SofaScore data source)
Date: February 16, 2026
Based on the exact logic from 4.11 Pass Networks.ipynb

NOTE: SofaScore's unofficial API may not expose individual pass events with
x/y coordinates.  This script attempts multiple known endpoints.  If pass-
level coordinate data is unavailable, it falls back to an average-position
approach using the lineups/heatmap data.
"""

import math
import json
import time
import requests
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SOFASCORE_EVENT_ID = 14083491
TEAM_NAME = "Barcelona"
OUTPUT_IMG = "barcelona_girona_passnetwork_ss.png"

# SofaScore uses 0-100 coords; StatsBomb uses 0-120 x 0-80
SCALE_X = 1.20
SCALE_Y = 0.80

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}

BASE_URL = "https://www.sofascore.com/api/v1"


# ---------------------------------------------------------------------------
# STEP 1 - Fetch data from SofaScore API
# ---------------------------------------------------------------------------

def api_get(path, retries=3, delay=2):
    """GET a SofaScore API endpoint with retry logic."""
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json()
            print(f"  [{r.status_code}] {url}")
        except requests.RequestException as e:
            print(f"  Request error: {e}")
        if attempt < retries - 1:
            time.sleep(delay)
    return None


def fetch_match_info(event_id):
    """Get basic match info (teams, score, etc.)."""
    return api_get(f"/event/{event_id}")


def fetch_incidents(event_id):
    """Get match incidents (goals, cards, subs, etc.)."""
    return api_get(f"/event/{event_id}/incidents")


def fetch_lineups(event_id):
    """Get team lineups with player IDs and jersey numbers."""
    return api_get(f"/event/{event_id}/lineups")


def fetch_statistics(event_id):
    """Get match statistics."""
    return api_get(f"/event/{event_id}/statistics")


def fetch_shotmap(event_id):
    """Get shot map (shots with coordinates)."""
    return api_get(f"/event/{event_id}/shotmap")


def fetch_coordinates(event_id):
    """
    Try the coordinates / average positions endpoint.
    This returns average x/y per player (not individual passes).
    """
    return api_get(f"/event/{event_id}/coordinates")


def fetch_pass_data(event_id):
    """
    Try several possible endpoints that might hold individual pass events.
    SofaScore doesn't officially expose these, so we try multiple paths.
    """
    candidates = [
        f"/event/{event_id}/graph",
        f"/event/{event_id}/events",
        f"/event/{event_id}/passes",
    ]
    for path in candidates:
        print(f"  Trying {path} ...")
        data = api_get(path)
        if data:
            return data, path
    return None, None


# ---------------------------------------------------------------------------
# STEP 2 - Build DataFrame from SofaScore data
# ---------------------------------------------------------------------------

def identify_team_id(match_info, team_name):
    """Return the SofaScore team id for the given name."""
    event = match_info.get("event", {})
    home = event.get("homeTeam", {})
    away = event.get("awayTeam", {})

    for t in [home, away]:
        if team_name.lower() in t.get("name", "").lower():
            return t.get("id")
    raise ValueError(
        f"Team '{team_name}' not found. "
        f"Available: {home.get('name')}, {away.get('name')}"
    )


def build_dataframe_from_coordinates_and_incidents(
    match_info, lineups_data, incidents_data, team_name
):
    """
    Fallback: build a pass-network-like visualisation from:
      - lineups  (player average positions / jersey numbers)
      - incidents (substitution times)

    This won't reproduce a true 4.11-style pass network (because we
    lack individual pass events), but it will show average player positions
    on the pitch, which is the best SofaScore data allows.
    """
    team_id = identify_team_id(match_info, team_name)

    # Find our team in lineups
    is_home = (
        match_info["event"]["homeTeam"]["id"] == team_id
    )
    lineup_key = "home" if is_home else "away"
    players_raw = lineups_data.get(lineup_key, {}).get("players", [])

    rows = []
    for p in players_raw:
        player = p.get("player", {})
        stats  = p.get("statistics", {})
        pos    = p.get("position", "")

        # averageX / averageY come from the statistics block if available
        avg_x = stats.get("averageX")
        avg_y = stats.get("averageY")

        if avg_x is not None and avg_y is not None:
            rows.append({
                "player_id":     player.get("id"),
                "player_name":   player.get("name", "Unknown"),
                "jersey_number": player.get("jerseyNumber"),
                "position":      pos,
                "x":             avg_x * SCALE_X,
                "y":             avg_y * SCALE_Y,
                "substitute":    p.get("substitute", False),
            })

    df = pd.DataFrame(rows)
    print(f"Built positions DataFrame: {len(df)} players for {team_name}")

    # Find first sub time from incidents
    first_sub_minute = None
    if incidents_data:
        for inc in incidents_data.get("incidents", []):
            if inc.get("incidentType") == "substitution":
                inc_team = inc.get("homeTeam" if is_home else "awayTeam")
                # Some formats nest differently
                if inc.get("isHome") == is_home or inc_team:
                    m = inc.get("time")
                    if m is not None:
                        if first_sub_minute is None or m < first_sub_minute:
                            first_sub_minute = m

    # Filter out substitutes (players who came on after the first sub)
    if first_sub_minute is not None:
        df = df[df["substitute"] == False]

    return df, first_sub_minute


# ---------------------------------------------------------------------------
# STEP 3 - Draw (adapted for positions-only mode)
# ---------------------------------------------------------------------------

def draw_positions_only(df, title=""):
    """
    When we only have average positions (no pass edges), draw the nodes
    with jersey numbers on a vertical pitch.
    """
    pitch = VerticalPitch(pitch_type="statsbomb")
    fig, ax = pitch.draw(figsize=(12, 8))

    pitch.scatter(
        df.x, df.y,
        s=500,
        color="#f0ece2",
        edgecolors="#010101",
        linewidth=2,
        alpha=1,
        ax=ax,
        zorder=2,
    )

    # Add jersey numbers
    for _, row in df.iterrows():
        jn = row.get("jersey_number", "")
        if jn:
            pitch.annotate(
                str(int(jn)),
                xy=(row.x, row.y),
                c="#132743",
                va="center",
                ha="center",
                size=10,
                fontweight="bold",
                ax=ax,
            )

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG, dpi=150, bbox_inches="tight")
    print(f"Saved: {OUTPUT_IMG}")
    plt.show()


# ---------------------------------------------------------------------------
# Full 4.11 pass network drawing (if we get actual pass events)
# ---------------------------------------------------------------------------

def pass_line_template(ax, x, y, end_x, end_y, line_color):
    ax.annotate(
        "",
        xy=(end_y, end_x),
        xytext=(y, x),
        zorder=1,
        arrowprops=dict(
            arrowstyle="-|>", linewidth=4, color=line_color, alpha=0.85
        ),
    )


def pass_line_template_shrink(ax, x, y, end_x, end_y, line_color,
                              dist_delta=1.2):
    dist  = math.hypot(end_x - x, end_y - y)
    angle = math.atan2(end_y - y, end_x - x)
    upd_x = x + (dist - dist_delta) * math.cos(angle)
    upd_y = y + (dist - dist_delta) * math.sin(angle)
    pass_line_template(ax, x, y, upd_x, upd_y, line_color=line_color)


def draw_full_network(average_locs_and_count, passes_between, title=""):
    pitch = VerticalPitch(pitch_type="statsbomb")
    fig, ax = pitch.draw(figsize=(12, 8))

    for _, row in passes_between.iterrows():
        pass_line_template_shrink(
            ax, row["x"], row["y"], row["x_end"], row["y_end"], "black"
        )

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

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG, dpi=150, bbox_inches="tight")
    print(f"Saved: {OUTPUT_IMG}")
    plt.show()


# ---------------------------------------------------------------------------
# 4.11 notebook logic (used if we get actual pass event data)
# ---------------------------------------------------------------------------

def process_passes_411(df):
    """Exact replica of the 4.11 notebook processing."""
    df["newsecond"] = 60 * df["minute"] + df["second"]
    df = df.sort_values(by=["newsecond"]).reset_index(drop=True)

    df["passer"]    = df["player_id"]
    df["recipient"] = df["passer"].shift(-1)

    passes_df = df.loc[df["type"] == "Pass"].copy()
    passes_df["pass_outcome"] = passes_df["pass_outcome"].fillna("Successful")
    completions = passes_df.loc[passes_df["pass_outcome"] == "Successful"]

    sub_df    = df.loc[df["type"].isin(["Substitution", "SubstitutionOff"])]
    first_sub = sub_df["newsecond"].min()
    if pd.isna(first_sub) or first_sub <= (60 * 45):
        first_sub = 60 * 45

    completions = completions.loc[completions["newsecond"] < first_sub]

    average_locs_and_count = (
        completions.groupby("passer")
        .agg({"x": ["mean"], "y": ["mean", "count"]})
    )
    average_locs_and_count.columns = ["x", "y", "count"]

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
    passes_between = passes_between.loc[passes_between["pass_count"] >= 4]

    return average_locs_and_count, passes_between


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== SofaScore Pass Network ===")
    print(f"Event ID : {SOFASCORE_EVENT_ID}")
    print(f"Team     : {TEAM_NAME}\n")

    # 1. Fetch basic info
    print("Fetching match info ...")
    match_info = fetch_match_info(SOFASCORE_EVENT_ID)
    if not match_info:
        raise SystemExit("Could not fetch match info from SofaScore.")

    event = match_info.get("event", {})
    home = event.get("homeTeam", {}).get("name", "?")
    away = event.get("awayTeam", {}).get("name", "?")
    print(f"Match: {home} vs {away}\n")

    # 2. Try to get actual pass events (unlikely but we try)
    print("Looking for pass-level event data ...")
    pass_data, endpoint = fetch_pass_data(SOFASCORE_EVENT_ID)

    if pass_data and isinstance(pass_data, dict):
        # Check if it looks like an events list
        events_list = pass_data.get("events") or pass_data.get("passes")
        if events_list and isinstance(events_list, list) and len(events_list) > 0:
            sample = events_list[0]
            if "x" in sample and "y" in sample:
                print(f"Found pass data via {endpoint} with {len(events_list)} events!")
                # TODO: convert to DataFrame and run process_passes_411
                # This path is kept for future compatibility but is currently
                # unlikely to be reached with SofaScore's public API.

    # 3. Fallback: use lineups + incidents for average-position plot
    print("\nPass-level data not available from SofaScore.")
    print("Falling back to average player positions from lineups.\n")

    print("Fetching lineups ...")
    lineups = fetch_lineups(SOFASCORE_EVENT_ID)
    if not lineups:
        raise SystemExit("Could not fetch lineups from SofaScore.")

    print("Fetching incidents ...")
    incidents = fetch_incidents(SOFASCORE_EVENT_ID)

    df_positions, first_sub = build_dataframe_from_coordinates_and_incidents(
        match_info, lineups, incidents, TEAM_NAME
    )

    if df_positions.empty:
        raise SystemExit(
            "No position data found. The match may not have been played yet, "
            "or SofaScore has not published average positions."
        )

    print(f"First substitution at minute: {first_sub}\n")

    draw_positions_only(
        df_positions,
        title=(
            f"{TEAM_NAME} Average Positions (SofaScore)\n"
            f"Girona vs Barcelona - 16/02/2026\n"
            f"(Pass edges unavailable - SofaScore does not expose individual pass events)"
        ),
    )
