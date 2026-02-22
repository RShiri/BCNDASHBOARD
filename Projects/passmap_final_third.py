"""
Final Third Entry Pass Maps – Girona vs Barcelona (16/02/2026)
Adapted from 4.8 Passmaps notebook, using cached WhoScored data.

Generates two images:
  - barcelona_final_third_entries.png
  - girona_final_third_entries.png
"""

import json, os
import pandas as pd
from mplsoccer import Pitch
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE    = os.path.join(_PROJECT_ROOT, "match_1914105_cache.json")
MATCH_LABEL   = "Girona vs Barcelona (16/02/2026)"

# WhoScored 0-100 → StatsBomb 0-120 x 0-80
SCALE_X = 1.20
SCALE_Y = 0.80

# Final third starts at x = 80 in StatsBomb coordinates
FINAL_THIRD_X = 80.0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
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
    """
    Build a DataFrame of all passes for *team_name* with columns:
        x, y, end_x, end_y, pass_outcome   (all in StatsBomb scale)
    """
    tid = _team_id(match_data, team_name)

    rows = []
    for ev in match_data.get("events", []):
        if ev.get("type", {}).get("displayName") != "Pass":
            continue
        if ev.get("teamId") != tid:
            continue

        outcome = ev.get("outcomeType", {}).get("displayName", "")
        end_x_raw = ev.get("endX")
        end_y_raw = ev.get("endY")
        if end_x_raw is None or end_y_raw is None:
            continue

        rows.append({
            "x":            ev.get("x", 0) * SCALE_X,
            "y":            80 - ev.get("y", 0) * SCALE_Y,   # flip Y
            "end_x":        float(end_x_raw) * SCALE_X,
            "end_y":        80 - float(end_y_raw) * SCALE_Y,  # flip Y
            "pass_outcome": "Complete" if outcome == "Successful" else "Incomplete",
        })

    return pd.DataFrame(rows)


def draw_final_third(df, team_name, out_file):
    """
    Plot comet lines for passes entering the final third, like 4.8 notebook.
    Green = complete, Red = incomplete.
    """
    # Filter: origin before the final third, destination inside
    entries = df[(df["x"] < FINAL_THIRD_X) & (df["end_x"] >= FINAL_THIRD_X)].copy()

    pitch = Pitch(pitch_type="statsbomb")
    fig, ax = pitch.draw(figsize=(12, 8))

    for _, row in entries.iterrows():
        color = "g" if row["pass_outcome"] == "Complete" else "r"
        pitch.lines(
            row["x"], row["y"], row["end_x"], row["end_y"],
            lw=5, transparent=True, comet=True, ax=ax, color=color,
        )

    # Count stats for title
    n_total    = len(entries)
    n_complete = (entries["pass_outcome"] == "Complete").sum()

    ax.set_title(
        f"{team_name} – Final Third Entries ({n_complete}/{n_total} complete)\n{MATCH_LABEL}",
        fontsize=14, fontweight="bold", fontfamily="monospace", pad=10,
    )

    # Legend
    legend_elements = [
        Line2D([0], [0], color="g", lw=4, label="Complete Pass"),
        Line2D([0], [0], color="r", lw=4, label="Incomplete Pass"),
    ]
    ax.legend(handles=legend_elements, loc="lower left")

    plt.tight_layout()
    plt.savefig(out_file, dpi=150, bbox_inches="tight")
    print(f"Saved: {os.path.basename(out_file)}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Final Third Entry Pass Maps ===\n")

    match_data = load_cache()
    print(f"Loaded {len(match_data.get('events', []))} events from cache.\n")

    for team in ("Barcelona", "Girona"):
        out = os.path.join(_PROJECT_ROOT, f"{team.lower()}_final_third_entries.png")
        print(f"--- {team} ---")
        df = build_pass_df(match_data, team)
        print(f"  Total passes: {len(df)}")
        draw_final_third(df, team, out)

    print("\nDone!")
