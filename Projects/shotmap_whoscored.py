"""
Enhanced Shot Maps – Girona vs Barcelona (16/02/2026)
Adapted from 4.9 Shotmaps notebook, using cached WhoScored data.

Improvements over 4.9:
  • Separate half-pitch (VerticalPitch) per team
  • xG-based colour gradient (cool→warm)
  • Player name + minute annotations beside each shot
  • Grass-textured pitch with alternating stripe pattern
  • Rich summary stats in the subtitle
  • BigChance / Penalty detection → 3× size multiplier
  • Interactive HTML version with hover tooltips (Plotly)

Generates:
  - barcelona_shotmap.png  +  barcelona_shotmap.html
  - girona_shotmap.png     +  girona_shotmap.html
"""

import json, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from mplsoccer import VerticalPitch
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE    = os.path.join(_PROJECT_ROOT, "match_1914105_cache.json")
MATCH_LABEL   = "Girona vs Barcelona (16/02/2026)"

# WhoScored 0-100 → StatsBomb coordinate conversion
# Simple 1.20 linear scaling has ~1-unit error at key landmarks.
# Calibrated piecewise-linear mapping instead:
#   WS 0   → SB 0
#   WS 50  → SB 60   (halfway line)
#   WS 89  → SB 108  (penalty spot)
#   WS 100 → SB 120  (goal line)
SCALE_Y = 0.80  # y: WhoScored 0-100 → StatsBomb 0-80 (linear, no offset)


def _ws_to_sb_x(ws_x):
    """Piecewise-linear WhoScored x → StatsBomb x using calibration points."""
    # Segments: [0→0, 50→60], [50→60, 89→108], [89→108, 100→120]
    if ws_x <= 50:
        return ws_x * (60.0 / 50.0)    # 1.20
    elif ws_x <= 89:
        return 60.0 + (ws_x - 50) * (48.0 / 39.0)  # ≈1.231 per unit
    else:
        return 108.0 + (ws_x - 89) * (12.0 / 11.0)  # ≈1.091 per unit


# xG colour map: low xG → blue/cool, high xG → red/warm
XG_CMAP = plt.cm.RdYlGn  # reversed later so low=red, high=green


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


def _player_name(match_data, player_id):
    """Look up short player name (surname) from match_data."""
    for side in ("home", "away"):
        for p in match_data.get(side, {}).get("players", []):
            if p.get("playerId") == player_id:
                name = p.get("name", "")
                parts = name.split()
                if len(parts) >= 2:
                    return parts[-1]
                return name
    return str(player_id)


def _player_full_name(match_data, player_id):
    """Look up full player name from match_data."""
    for side in ("home", "away"):
        for p in match_data.get(side, {}).get("players", []):
            if p.get("playerId") == player_id:
                return p.get("name", str(player_id))
    return str(player_id)


def _is_shot(ev):
    """WhoScored uses satisfiedEventsTypes to identify shots.
    Shot event types include: 13 (miss), 14 (post), 15 (attempt saved), 16 (goal)
    Also check qualifiers for the 'isGoal' type or shotType flags.
    Simplest: check the type displayName directly."""
    type_name = ev.get("type", {}).get("displayName", "")
    return type_name in ("MissedShots", "SavedShot", "ShotOnPost", "Goal")


def _shot_is_goal(ev):
    return ev.get("type", {}).get("displayName", "") == "Goal"


def _shot_is_on_target(ev):
    type_name = ev.get("type", {}).get("displayName", "")
    return type_name in ("SavedShot", "Goal")


def _estimate_xg(x_sb, y_sb, is_penalty, is_big_chance, body_part):
    """
    Very rough geometry-based expected goals, augmented with event qualifiers.
    Penalties strictly 0.76. Big chances boosted. Headers discounted.
    """
    if is_penalty:
        return 0.76

    goal_x, goal_y = 120.0, 40.0
    dx = goal_x - x_sb
    dy = goal_y - y_sb
    distance = max(np.sqrt(dx**2 + dy**2), 0.5)

    half_goal = 4.0
    angle = np.arctan2(half_goal, distance)

    xg = (angle / (np.pi / 2)) * (1 / (1 + distance / 30))

    if body_part == "Header":
        xg *= 0.4
    
    if is_big_chance:
        xg = max(0.35, xg * 3.5)
        xg = min(0.65, xg)
        
    if distance > 18:
        xg *= (18 / distance)**2

    return round(min(max(xg, 0.01), 0.95), 3)


def _extract_qualifiers(ev):
    """Extract useful qualifier tags from a WhoScored shot event."""
    quals = {q.get("type", {}).get("displayName", "")
             for q in ev.get("qualifiers", [])}

    # Body part
    body = "Right Foot" if "RightFoot" in quals else \
           "Left Foot"  if "LeftFoot"  in quals else \
           "Header"     if "Head"      in quals else "Unknown"

    # Situation
    situation = "Penalty"     if "Penalty"     in quals else \
                "Free Kick"   if "DirectFreekick" in quals else \
                "Fast Break"  if "FastBreak"   in quals else \
                "Set Piece"   if "SetPiece"    in quals else \
                "Corner"      if "FromCorner"  in quals else \
                "Open Play"

    # Location zone (from WhoScored qualifiers — more accurate than coords)
    if any(z in quals for z in ("SmallBoxCentre", "SmallBoxLeft", "SmallBoxRight",
                                 "DeepBoxCentre", "DeepBoxLeft", "DeepBoxRight")):
        zone = "6-Yard Box"
    elif any(z in quals for z in ("BoxCentre", "BoxLeft", "BoxRight")):
        zone = "Inside Box"
    elif any(z in quals for z in ("OutOfBoxCentre", "OutOfBoxLeft", "OutOfBoxRight")):
        zone = "Outside Box"
    else:
        zone = "Unknown"

    big_chance = "BigChance" in quals
    one_on_one = "OneOnOne"  in quals

    return body, situation, zone, big_chance, one_on_one


def build_shot_df(match_data, team_name):
    """
    Build a DataFrame of shots for *team_name* with columns:
        x, y, minute, player, is_goal, is_on_target, xG,
        body_part, situation, zone, big_chance, one_on_one
    """
    tid = _team_id(match_data, team_name)
    rows = []

    for ev in match_data.get("events", []):
        if ev.get("teamId") != tid:
            continue
        if not _is_shot(ev):
            continue

        x_sb = _ws_to_sb_x(ev.get("x", 0))
        y_sb = 80 - ev.get("y", 0) * SCALE_Y  # flip Y
        body, situation, zone, big_chance, one_on_one = _extract_qualifiers(ev)

        # Override coordinates for penalties → place exactly at penalty spot
        is_penalty = (situation == "Penalty")
        if is_penalty:
            x_sb = 108.0  # StatsBomb penalty spot x
            y_sb = 40.0   # StatsBomb centre y

        rows.append({
            "x":            x_sb,
            "y":            y_sb,
            "minute":       ev.get("minute", 0),
            "player":       _player_name(match_data, ev.get("playerId")),
            "full_name":    _player_full_name(match_data, ev.get("playerId")),
            "is_goal":      _shot_is_goal(ev),
            "is_on_target": _shot_is_on_target(ev),
            "xG":           _estimate_xg(x_sb, y_sb, is_penalty, big_chance, body),
            "body_part":    body,
            "situation":    situation,
            "zone":         zone,
            "big_chance":   big_chance,
            "one_on_one":   one_on_one,
        })

    return pd.DataFrame(rows)


def rescale_xg_to_total(df, target_total):
    """
    Scale non-penalty shots so the team total matches target_total.
    Penalties are locked at 0.76 (Understat's exact constant).
    """
    if df.empty or target_total is None:
        return df
        
    df = df.copy()
    
    # Identify penalties vs non-penalties
    is_pen = df["situation"] == "Penalty"
    
    # Ensure penalties are exactly 0.76
    df.loc[is_pen, "xG"] = 0.76
    
    pen_xg_sum = 0.76 * is_pen.sum()
    non_pen_target = target_total - pen_xg_sum
    
    if non_pen_target <= 0:
        return df
        
    non_pen_current = df.loc[~is_pen, "xG"].sum()
    if non_pen_current <= 0:
        return df
        
    # Scale only the non-penalty shots
    multiplier = non_pen_target / non_pen_current
    df.loc[~is_pen, "xG"] = (df.loc[~is_pen, "xG"] * multiplier).round(3)
    df["xG"] = df["xG"].clip(upper=0.99)
    return df


def draw_shotmap(df, team_name, out_file):
    """
    Draw an enhanced half-pitch shot map with dark theme.
    """
    # --- Pitch setup (half-pitch, grass-textured) ---
    pitch = VerticalPitch(
        pitch_type="statsbomb",
        half=True,
        pitch_color="#2d572c",       # base grass green
        line_color="#ffffff",
        linewidth=2,
        stripe=True,                  # alternating stripe bands
        stripe_color="#234f22",       # darker stripe for realism
    )
    fig, ax = pitch.draw(figsize=(10, 10))
    fig.set_facecolor("#1a1a2e")     # dark border around the pitch

    if df.empty:
        ax.set_title(
            f"{team_name} Shot Map\n{MATCH_LABEL}\nNo shots recorded",
            fontsize=16, fontweight="bold", color="white", pad=20,
        )
        plt.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return

    # --- Normalize xG for colour mapping ---
    xg_vals = df["xG"].values
    norm = mcolors.Normalize(vmin=0, vmax=max(xg_vals.max(), 0.4))

    # --- Plot shots ---
    for _, row in df.iterrows():
        colour = XG_CMAP(norm(row["xG"]))
        marker = "*" if row["is_goal"] else "o"
        # Base sizing (4.9 notebook), 3× boost for BigChance / Penalty
        size = 500 * row["xG"]
        if row.get("big_chance", False) or row.get("situation") == "Penalty":
            size *= 3

        pitch.scatter(
            row["x"], row["y"],
            s=size,
            marker=marker,
            color=colour,
            edgecolors="white" if row["is_goal"] else "#555555",
            linewidth=2 if row["is_goal"] else 1,
            alpha=0.9,
            zorder=3,
            ax=ax,
        )

        # annotation: Player (min')
        label = f"{row['player']} ({int(row['minute'])}')"
        ax.annotate(
            label,
            xy=(row["y"], row["x"]),   # VerticalPitch: (y, x) for text
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=7,
            fontweight="bold",
            color="white",
            alpha=0.85,
            zorder=4,
        )

    # --- Stats for subtitle ---
    n_shots    = len(df)
    n_on_target = int(df["is_on_target"].sum())
    n_goals    = int(df["is_goal"].sum())
    total_xg   = df["xG"].sum()

    subtitle = (
        f"Shots: {n_shots}  |  On Target: {n_on_target}  |  "
        f"Goals: {n_goals}  |  xG: {total_xg:.2f}"
    )

    # --- Title & subtitle (using fig-level text for full control) ---
    fig.suptitle(
        f"{team_name} Shot Map",
        fontsize=20, fontweight="bold", color="white",
        y=0.98,
    )
    fig.text(
        0.5, 0.935, MATCH_LABEL,
        ha="center", fontsize=14, fontweight="bold", color="white",
    )
    fig.text(
        0.5, 0.91, subtitle,
        ha="center", fontsize=11, fontfamily="monospace",
        color="#cccccc",
    )

    # --- Legend ---
    legend_elements = [
        Line2D([0], [0], marker="*", color="#2d572c", markerfacecolor="#66bb6a",
               markersize=14, markeredgecolor="white", markeredgewidth=1.5,
               label="Goal"),
        Line2D([0], [0], marker="o", color="#2d572c", markerfacecolor="#ef5350",
               markersize=10, markeredgecolor="#555555", markeredgewidth=1,
               label="No Goal"),
        Line2D([0], [0], marker="D", color="#2d572c", markerfacecolor="#ffd700",
               markersize=12, markeredgecolor="white", markeredgewidth=1,
               label="Big Chance / Penalty (3×)"),
    ]
    # Add xG scale dots
    for xg_val in (0.05, 0.15, 0.30):
        sz = 500 * xg_val
        legend_elements.append(
            Line2D([0], [0], marker="o", color="#2d572c",
                   markerfacecolor=XG_CMAP(norm(xg_val)),
                   markersize=np.sqrt(sz) / 2,
                   markeredgecolor="#555555", markeredgewidth=0.5,
                   label=f"xG = {xg_val}")
        )

    legend = ax.legend(
        handles=legend_elements,
        loc="lower left",
        fontsize=9,
        framealpha=0.85,
        facecolor="#1a3a19",
        edgecolor="#4a7a49",
        labelcolor="white",
        title="Shot Legend",
        title_fontsize=10,
    )
    legend.get_title().set_color("white")

    plt.tight_layout()
    plt.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved: {os.path.basename(out_file)}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# INTERACTIVE HTML SHOT MAP (Plotly)
# ---------------------------------------------------------------------------
def draw_interactive_shotmap(df, team_name, out_html):
    """
    Create an interactive HTML shot map with hover tooltips using Plotly.
    Hover shows: player, minute, xG, outcome, body part, situation, zone.
    """
    if df.empty:
        print(f"  No shots for {team_name}, skipping interactive map.")
        return

    # Prepare data ---------------------------------------------------------
    # On VerticalPitch the axes are (y, x) — x is vertical, y is horizontal
    # For Plotly we plot y on x-axis and x on y-axis to get a vertical view
    plot_x = df["y"].values       # horizontal position
    plot_y = df["x"].values       # vertical position (distance from goal)

    # Colour per xG
    norm = mcolors.Normalize(vmin=0, vmax=max(df["xG"].max(), 0.4))
    colors = [f"rgba({int(r*255)},{int(g*255)},{int(b*255)},0.55)"
              for r, g, b, a in [XG_CMAP(norm(v)) for v in df["xG"]]]

    # Size: 500*xG with 3× boost for BigChance / Penalty
    sizes = []
    for _, row in df.iterrows():
        s = 500 * row["xG"]
        if row.get("big_chance", False) or row.get("situation") == "Penalty":
            s *= 3
        sizes.append(max(s, 8))  # minimum visible size

    # Marker symbols
    symbols = ["star" if g else "circle" for g in df["is_goal"]]
    edge_colors = ["white" if g else "#555555" for g in df["is_goal"]]

    # Hover text
    hover_texts = []
    for _, row in df.iterrows():
        outcome = "Goal ⚽" if row["is_goal"] else (
            "On Target" if row["is_on_target"] else "Off Target")
        tags = []
        if row.get("big_chance"):
            tags.append("⭐ Big Chance")
        if row.get("situation") == "Penalty":
            tags.append("🎯 Penalty")
        if row.get("one_on_one"):
            tags.append("1v1")
        tag_line = "  |  ".join(tags) if tags else ""

        text = (
            f"<b>{row.get('full_name', row['player'])}</b> ({int(row['minute'])}')<br>"
            f"Outcome: {outcome}<br>"
            f"xG: {row['xG']:.3f}<br>"
            f"Body: {row.get('body_part', '?')}  |  {row.get('situation', '?')}<br>"
            f"Zone: {row.get('zone', '?')}"
        )
        if tag_line:
            text += f"<br><b>{tag_line}</b>"
        hover_texts.append(text)

    # Build figure ---------------------------------------------------------
    n_shots = len(df)
    n_goals = int(df["is_goal"].sum())
    total_xg = df["xG"].sum()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=plot_x, y=plot_y,
        mode="markers",
        marker=dict(
            size=[np.sqrt(s) * 1.2 for s in sizes],
            color=colors,
            symbol=symbols,
            line=dict(width=1.5, color=edge_colors),
        ),
        hovertext=hover_texts,
        hoverinfo="text",
    ))

    # Draw pitch outline (half-pitch, StatsBomb coords) --------------------
    # Penalty box, goal box, centre circle (top arc), touchlines
    pitch_shapes = [
        # Touchlines (half pitch: x from 60 to 120, y from 0 to 80)
        dict(type="rect", x0=0, y0=60, x1=80, y1=120,
             line=dict(color="white", width=2)),
        # Penalty area (18-yard box)
        dict(type="rect", x0=18, y0=102, x1=62, y1=120,
             line=dict(color="white", width=1.5)),
        # 6-yard box
        dict(type="rect", x0=30, y0=114, x1=50, y1=120,
             line=dict(color="white", width=1.5)),
        # Penalty spot (small white dot)
        dict(type="circle", x0=39.5, y0=107.5, x1=40.5, y1=108.5,
             line=dict(color="white", width=0.5), fillcolor="white"),
        # Centre circle arc (bottom portion visible)
        dict(type="circle", x0=30, y0=50, x1=50, y1=70,
             line=dict(color="white", width=1.5)),
        # Halfway line
        dict(type="line", x0=0, y0=60, x1=80, y1=60,
             line=dict(color="white", width=1.5)),
    ]

    fig.update_layout(
        title=dict(
            text=(
                f"<b>{team_name} Shot Map</b><br>"
                f"<span style='font-size:14px'>{MATCH_LABEL}</span><br>"
                f"<span style='font-size:12px;color:#cccccc'>"
                f"Shots: {n_shots}  |  Goals: {n_goals}  |  xG: {total_xg:.2f}</span>"
            ),
            x=0.5, font=dict(size=18, color="white"),
        ),
        plot_bgcolor="#2d572c",
        paper_bgcolor="#1a1a2e",
        font=dict(color="white"),
        shapes=pitch_shapes,
        xaxis=dict(
            range=[-5, 85], showgrid=False, zeroline=False,
            showticklabels=False, fixedrange=True,
        ),
        yaxis=dict(
            range=[55, 125], showgrid=False, zeroline=False,
            showticklabels=False, fixedrange=True,
            scaleanchor="x",
        ),
        showlegend=True,
        legend=dict(
            x=0.01, y=0.01, xanchor="left", yanchor="bottom",
            bgcolor="rgba(26,58,25,0.85)",
            bordercolor="#4a7a49", borderwidth=1,
            font=dict(color="white", size=11),
            title=dict(text="Shot Legend", font=dict(color="white", size=12)),
        ),
        width=700, height=700,
        margin=dict(l=20, r=20, t=100, b=20),
    )

    # --- Legend traces (invisible points, just for the legend) ---
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Goal",
        marker=dict(size=14, symbol="star", color="#66bb6a",
                    line=dict(width=1.5, color="white")),
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="No Goal",
        marker=dict(size=10, symbol="circle", color="#ef5350",
                    line=dict(width=1, color="#555555")),
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name="Big Chance / Penalty (3×)",
        marker=dict(size=12, symbol="diamond", color="#ffd700",
                    line=dict(width=1, color="white")),
    ))

    fig.write_html(out_html)
    print(f"Saved interactive: {os.path.basename(out_html)}")



# ---------------------------------------------------------------------------
# COMBINED SHOT MAP (both teams, one pitch)
# ---------------------------------------------------------------------------

def draw_combined_shotmap(df_home, home_name, df_away, away_name, out_html,
                          xg_override_home=None, xg_override_away=None, match_label=""):
    """
    Full-pitch Plotly interactive shot map showing both teams.
    Home attacks left→right
    Away is mirrored so they also attack toward right end,
    but displayed on the LEFT side.
    """
    import math

    PITCH_LENGTH = 120.0
    PITCH_WIDTH  = 80.0

    HOME_COLOR  = "#a50044"   # Girona red
    AWAY_COLOR  = "#004d98"   # Barcelona blue

    def prep_team(df, team_color, mirror=False):
        """Prepare scatter data for one team. mirror=True flips x to other end."""
        plot_x, plot_y, colors, sizes, symbols, edge_colors, hover_texts = [], [], [], [], [], [], []

        xg_vals = df["xG"].values
        xg_min, xg_max = xg_vals.min() if len(xg_vals) else 0, xg_vals.max() if len(xg_vals) else 1
        xg_range = max(xg_max - xg_min, 0.01)

        for _, row in df.iterrows():
            px = (PITCH_LENGTH - row["x"]) if mirror else row["x"]
            py = row["y"]

            # Size
            base_s = 40 + (row["xG"] - xg_min) / xg_range * 280
            size_boost = 2.5 if (row.get("big_chance") or row.get("situation") == "Penalty") else 1.0
            sizes.append(base_s * size_boost)

            # Symbol
            symbols.append("star" if row["is_goal"] else "circle")

            # Color – team base with alpha based on xG
            t = (row["xG"] - xg_min) / xg_range
            alpha = 0.45 + 0.40 * t  # 0.45 → 0.85
            import re
            r = int(team_color[1:3], 16)
            g = int(team_color[3:5], 16)
            b = int(team_color[5:7], 16)
            colors.append(f"rgba({r},{g},{b},{alpha:.2f})")
            edge_colors.append("white" if row["is_goal"] else "#333333")

            plot_x.append(px)
            plot_y.append(py)

            # Hover
            outcome = "Goal" if row["is_goal"] else ("On Target" if row["is_on_target"] else "Off Target")
            tags = []
            if row.get("big_chance"):   tags.append("Big Chance")
            if row.get("situation") == "Penalty": tags.append("Penalty")
            if row.get("one_on_one"):   tags.append("1v1")
            tag_line = "  |  ".join(tags)
            text = (
                f"<b>{row.get('full_name', row['player'])}</b> ({int(row['minute'])}')<br>"
                f"Outcome: {outcome}<br>"
                f"xG: {row['xG']:.3f}<br>"
                f"Body: {row.get('body_part','?')}  |  {row.get('situation','?')}<br>"
                f"Zone: {row.get('zone','?')}"
            )
            if tag_line:
                text += f"<br><b>{tag_line}</b>"
            hover_texts.append(text)

        return plot_x, plot_y, colors, sizes, symbols, edge_colors, hover_texts

    fig = go.Figure()

    # ── Away team (Barcelona) — mirrored to left side ──
    ax, ay, ac, as_, asym, aec, aht = prep_team(df_away, AWAY_COLOR, mirror=True)
    fig.add_trace(go.Scatter(
        x=ax, y=ay, mode="markers",
        name=away_name,
        marker=dict(size=[math.sqrt(s)*1.1 for s in as_], color=ac,
                    symbol=asym, line=dict(width=1.5, color=aec)),
        hovertext=aht, hoverinfo="text",
    ))

    # ── Home team (Girona) — normal orientation, right side ──
    hx, hy, hc, hs, hsym, hec, hht = prep_team(df_home, HOME_COLOR, mirror=False)
    # Mirror home so they attack toward x=0 (left side) — wait, let's keep
    # Girona on the RIGHT half naturally (their x is already near 100-120 for shots).
    # Actually WhoScored gives each team's stats from their OWN perspective,
    # so Girona's shot x values are near 80-100 (away end). We DON'T mirror Girona.
    fig.add_trace(go.Scatter(
        x=hx, y=hy, mode="markers",
        name=home_name,
        marker=dict(size=[math.sqrt(s)*1.1 for s in hs], color=hc,
                    symbol=hsym, line=dict(width=1.5, color=hec)),
        hovertext=hht, hoverinfo="text",
    ))

    # ────────────────── PITCH SHAPES ──────────────────
    W = PITCH_WIDTH    # 80
    L = PITCH_LENGTH   # 120

    pitch_shapes = [
        # Outer touchlines
        dict(type="rect", x0=0, y0=0, x1=L, y1=W,
             line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)"),
        # Halfway line
        dict(type="line", x0=60, y0=0, x1=60, y1=W, line=dict(color="white", width=1.5)),
        # Centre circle
        dict(type="circle", x0=60-9.15, y0=40-9.15, x1=60+9.15, y1=40+9.15,
             line=dict(color="white", width=1.5)),
        # Centre spot
        dict(type="circle", x0=59.5, y0=39.5, x1=60.5, y1=40.5,
             fillcolor="white", line=dict(color="white")),

        # LEFT penalty box  (x: 0→18)
        dict(type="rect", x0=0, y0=18, x1=18, y1=62,
             line=dict(color="white", width=1.5), fillcolor="rgba(0,0,0,0)"),
        # LEFT 6-yard box   (x: 0→6)
        dict(type="rect", x0=0, y0=30, x1=6, y1=50,
             line=dict(color="white", width=1), fillcolor="rgba(0,0,0,0)"),
        # LEFT penalty spot  x=12
        dict(type="circle", x0=11.5, y0=39.5, x1=12.5, y1=40.5,
             fillcolor="white", line=dict(color="white")),

        # RIGHT penalty box (x: 102→120)
        dict(type="rect", x0=102, y0=18, x1=L, y1=62,
             line=dict(color="white", width=1.5), fillcolor="rgba(0,0,0,0)"),
        # RIGHT 6-yard box  (x: 114→120)
        dict(type="rect", x0=114, y0=30, x1=L, y1=50,
             line=dict(color="white", width=1), fillcolor="rgba(0,0,0,0)"),
        # RIGHT penalty spot x=108
        dict(type="circle", x0=107.5, y0=39.5, x1=108.5, y1=40.5,
             fillcolor="white", line=dict(color="white")),

        # LEFT goal
        dict(type="rect", x0=-2, y0=36, x1=0, y1=44,
             line=dict(color="white", width=2), fillcolor="rgba(255,255,255,0.1)"),
        # RIGHT goal
        dict(type="rect", x0=L, y0=36, x1=L+2, y1=44,
             line=dict(color="white", width=2), fillcolor="rgba(255,255,255,0.1)"),
    ]

    # ── Divider label annotations ──
    annotations = [
        dict(x=30, y=80, text=f"← {away_name} Shots",
             showarrow=False, font=dict(color=AWAY_COLOR, size=14, family="Inter"),
             xanchor="center", yanchor="bottom", yshift=8),
        dict(x=90, y=80, text=f"{home_name} Shots →",
             showarrow=False, font=dict(color=HOME_COLOR, size=14, family="Inter"),
             xanchor="center", yanchor="bottom", yshift=8),
    ]

    n_home  = len(df_home)
    n_away  = len(df_away)
    g_home  = int(df_home["is_goal"].sum())
    g_away  = int(df_away["is_goal"].sum())
    xg_home = xg_override_home if xg_override_home is not None else round(df_home["xG"].sum(), 2)
    xg_away = xg_override_away if xg_override_away is not None else round(df_away["xG"].sum(), 2)

    fig.update_layout(
        title=dict(
            text=(
                f"<b style='color:{AWAY_COLOR}'>{away_name}</b>"
                f"  <span style='color:white;font-size:22px'>{g_away} – {g_home}</span>  "
                f"<b style='color:{HOME_COLOR}'>{home_name}</b><br>"
                f"<span style='font-size:13px;color:#cccccc'>{match_label}</span><br>"
                f"<span style='font-size:11px;color:#aaaaaa'>"
                f"{away_name}: {n_away} shots · xG {xg_away:.2f}  "
                f"| {home_name}: {n_home} shots · xG {xg_home:.2f}</span>"
            ),
            x=0.5, font=dict(size=18, color="white"),
        ),
        plot_bgcolor="#2d572c",
        paper_bgcolor="#1a1a2e",
        font=dict(color="white"),
        shapes=pitch_shapes,
        annotations=annotations,
        xaxis=dict(range=[-3, L+3], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        yaxis=dict(range=[-3, W+12], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True,
                   scaleanchor="x"),
        showlegend=True,
        legend=dict(
            x=0.5, y=-0.02, xanchor="center", yanchor="top",
            orientation="h",
            bgcolor="rgba(26,26,46,0.85)",
            bordercolor="#4444aa", borderwidth=1,
            font=dict(color="white", size=12),
        ),
        autosize=True, height=580,
        margin=dict(l=20, r=20, t=120, b=60),
    )

    # Legend traces
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Goal",
        marker=dict(size=14, symbol="star", color="rgba(255,255,255,0.9)",
                    line=dict(width=1.5, color="white"))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="No Goal",
        marker=dict(size=10, symbol="circle", color="rgba(200,200,200,0.5)",
                    line=dict(width=1, color="#555555"))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Big Chance / Penalty (3×)",
        marker=dict(size=12, symbol="diamond", color="rgba(255,215,0,0.8)",
                    line=dict(width=1, color="white"))))

    fig.write_html(out_html)
    print(f"Saved combined interactive: {os.path.basename(out_html)}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Enhanced Shot Maps ===\n")

    match_data = load_cache()
    print(f"Loaded {len(match_data.get('events', []))} events from cache.\n")

    dfs = {}
    for team in ("Barcelona", "Girona"):
        out_png  = os.path.join(_PROJECT_ROOT, f"{team.lower()}_shotmap.png")
        out_html = os.path.join(_PROJECT_ROOT, f"{team.lower()}_shotmap.html")
        print(f"--- {team} ---")
        df = build_shot_df(match_data, team)
        dfs[team] = df
        print(f"  Shots found: {len(df)}")
        if not df.empty:
            big_ct = df['big_chance'].sum()
            print(f"  Goals: {df['is_goal'].sum()}  |  Big Chances: {big_ct}")
            print(f"  Total xG (est.): {df['xG'].sum():.2f}")
        draw_shotmap(df, team, out_png)
        draw_interactive_shotmap(df, team, out_html)

    # ── Generate WhoScored (geometry) combined map BEFORE rescaling ──────────
    print("\n--- Combined Shot Map [WhoScored xG] ---")
    combined_ws_html = os.path.join(_PROJECT_ROOT, "combined_shotmap_ws.html")
    draw_combined_shotmap(
        dfs["Girona"], "Girona",
        dfs["Barcelona"], "Barcelona",
        combined_ws_html,
        # No overrides → use geometry xG as-is
    )

    # Fetch Understat xG totals to calibrate per-shot values
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fetch_understat_xg import fetch_understat_xg as _fetch_us
        _us_home, _us_away = _fetch_us()
        print(f"  Understat xG: Girona {_us_home}  Barcelona {_us_away}")
    except Exception as _e:
        print(f"  Understat fetch failed ({_e}), using geometry xG")
        _us_home = _us_away = None

    # Rescale per-shot xG to match Understat totals
    dfs["Girona"]    = rescale_xg_to_total(dfs["Girona"],    _us_home)
    dfs["Barcelona"] = rescale_xg_to_total(dfs["Barcelona"], _us_away)
    print(f"  Rescaled xG: Girona {dfs['Girona']['xG'].sum():.2f}  Barcelona {dfs['Barcelona']['xG'].sum():.2f}")

    # Regenerate individual interactive HTML maps with rescaled xG
    for team in ("Barcelona", "Girona"):
        out_html = os.path.join(_PROJECT_ROOT, f"{team.lower()}_shotmap.html")
        draw_interactive_shotmap(dfs[team], team, out_html)

    # ── Generate Understat combined map AFTER rescaling ───────────────────────
    print("\n--- Combined Shot Map [Understat xG] ---")
    combined_us_html = os.path.join(_PROJECT_ROOT, "combined_shotmap.html")
    draw_combined_shotmap(
        dfs["Girona"], "Girona",
        dfs["Barcelona"], "Barcelona",
        combined_us_html,
        xg_override_home=_us_home,
        xg_override_away=_us_away,
    )

    print("\nDone!")


