"""
Total and Progressive Pass Maps – Girona vs Barcelona (16/02/2026)
Generates high-fidelity static PNGs using mplsoccer for total and progressive passes.
"""

import json, os
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE    = os.path.join(_PROJECT_ROOT, "match_1914105_cache.json")
MATCH_LABEL   = "Girona vs Barcelona (16/02/2026)"

# WhoScored 0-100 -> StatsBomb 0-120 x 0-80
SCALE_X = 1.20
SCALE_Y = 0.80

def load_cache():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _team_id(match_data, team_name):
    for side in ("home", "away"):
        info = match_data.get(side, {})
        if team_name.lower() in info.get("name", "").lower():
            return info["teamId"]
    raise ValueError(f"Team '{team_name}' not found")

def build_pass_df(match_data, team_name):
    tid = _team_id(match_data, team_name)
    rows = []
    for ev in match_data.get("events", []):
        if ev.get("type", {}).get("displayName") != "Pass": continue
        if ev.get("teamId") != tid: continue

        outcome = ev.get("outcomeType", {}).get("displayName", "")
        end_x_raw = ev.get("endX")
        end_y_raw = ev.get("endY")
        if end_x_raw is None or end_y_raw is None: continue

        # Progressive pass logic (from backend/parser.py)
        is_prog = False
        if outcome == "Successful":
            x = ev.get("x", 0) * SCALE_X
            y = 80 - ev.get("y", 0) * SCALE_Y
            end_x = float(end_x_raw) * SCALE_X
            end_y = 80 - float(end_y_raw) * SCALE_Y

            if x >= 48:
                if x < 60 and (end_x - x) >= 30: is_prog = True
                elif 60 <= x <= 90 and (end_x - x) >= 15: is_prog = True
                elif x > 90 and (end_x - x) >= 10: is_prog = True

        rows.append({
            "x": ev.get("x", 0) * SCALE_X,
            "y": 80 - ev.get("y", 0) * SCALE_Y,
            "end_x": float(end_x_raw) * SCALE_X,
            "end_y": 80 - float(end_y_raw) * SCALE_Y,
            "pass_outcome": "Complete" if outcome == "Successful" else "Incomplete",
            "is_progressive": is_prog
        })
    return pd.DataFrame(rows)

def draw_pass_map(df, team_name, title_suffix, out_file, color_val="#004d98"):
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#2d572c", line_color="white")
    fig, ax = pitch.draw(figsize=(12, 8))

    successful = df[df["pass_outcome"] == "Complete"]
    failed = df[df["pass_outcome"] == "Incomplete"]

    # Only drawing successful for simplicity in these maps to avoid clutter like with total passes
    if not successful.empty:
        pitch.lines(
            successful["x"], successful["y"], successful["end_x"], successful["end_y"],
            lw=3, transparent=True, comet=True, ax=ax, color=color_val, alpha=0.6
        )
    
    ax.set_title(
        f"{team_name} - {title_suffix}\n{MATCH_LABEL}",
        fontsize=16, fontweight="bold", fontfamily="sans-serif", color="white", pad=15
    )
    
    fig.patch.set_facecolor('#0d0d1a')
    
    plt.tight_layout()
    plt.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
    print(f"Saved: {os.path.basename(out_file)}")
    plt.close(fig)

if __name__ == "__main__":
    match_data = load_cache()
    
    for team in ("Barcelona", "Girona"):
        df = build_pass_df(match_data, team)
        
        # Total Passes
        out_total = os.path.join(_PROJECT_ROOT, f"{team.lower()}_total_passes.png")
        draw_pass_map(df, team, "Total Successful Passes", out_total, color_val="#1f77b4" if team=="Girona" else "#a50044")
        
        # Progressive Passes
        prog_df = df[df["is_progressive"] == True]
        out_prog = os.path.join(_PROJECT_ROOT, f"{team.lower()}_progressive_passes.png")
        draw_pass_map(prog_df, team, f"Progressive Passes ({len(prog_df)})", out_prog, color_val="#edbb00")

    print("\nAll pass maps generated successfully!")
