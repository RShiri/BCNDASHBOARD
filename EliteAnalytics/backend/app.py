from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import math
import os

from EliteAnalytics.backend.database import get_session, Match, Team, Player, Event

app = FastAPI(title="Elite Barca Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(_ROOT)
app.mount("/static", StaticFiles(directory=os.path.join(_ROOT, "frontend", "static")), name="static")
app.mount("/assets", StaticFiles(directory=os.path.join(PROJECT_ROOT, "assets")), name="assets")

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/matches")
def get_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).order_by(Match.date.desc()).all()
    res = []
    for m in matches:
        res.append({
            "id": m.id,
            "date": m.date,
            "competition": m.competition,
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "home_score": m.home_score,
            "away_score": m.away_score
        })
    return res

@app.get("/api/matches/{match_id}/stats")
def get_match_stats(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    # Team IDs
    hid = match.home_team_id
    aid = match.away_team_id
    
    # Calculate xG
    home_xg = db.query(func.sum(Event.xg)).filter(Event.match_id==match_id, Event.team_id==hid, Event.is_shot==True).scalar() or 0
    away_xg = db.query(func.sum(Event.xg)).filter(Event.match_id==match_id, Event.team_id==aid, Event.is_shot==True).scalar() or 0
    
    # Possession
    home_passes = db.query(func.count(Event.id)).filter(Event.match_id==match_id, Event.team_id==hid, Event.type_name=="Pass").scalar() or 0
    away_passes = db.query(func.count(Event.id)).filter(Event.match_id==match_id, Event.team_id==aid, Event.type_name=="Pass").scalar() or 0
    total_passes = home_passes + away_passes or 1
    
    # Field Tilt (Possession in final third: x > 66.6)
    hf_passes = db.query(func.count(Event.id)).filter(Event.match_id==match_id, Event.team_id==hid, Event.type_name=="Pass", Event.x > 66.6).scalar() or 0
    af_passes = db.query(func.count(Event.id)).filter(Event.match_id==match_id, Event.team_id==aid, Event.type_name=="Pass", Event.x > 66.6).scalar() or 0
    total_f_passes = hf_passes + af_passes or 1

    # PPDA
    # Home PPDA = Away Passes in Home's Def 60% / Home Def Actions
    # Def actions = Tackle, Interception, Foul, Challenge
    h_def_actions = db.query(func.count(Event.id)).filter(Event.match_id==match_id, Event.team_id==hid, Event.type_name.in_(["Tackle", "Interception", "Foul", "Challenge"])).scalar() or 1
    a_def_actions = db.query(func.count(Event.id)).filter(Event.match_id==match_id, Event.team_id==aid, Event.type_name.in_(["Tackle", "Interception", "Foul", "Challenge"])).scalar() or 1
    
    return {
        "home_team": match.home_team.name,
        "away_team": match.away_team.name,
        "score": f"{match.home_score} - {match.away_score}",
        "home_xg": round(home_xg, 2),
        "away_xg": round(away_xg, 2),
        "home_possession": round((home_passes / total_passes)*100, 1),
        "away_possession": round((away_passes / total_passes)*100, 1),
        "home_field_tilt": round((hf_passes / total_f_passes)*100, 1),
        "away_field_tilt": round((af_passes / total_f_passes)*100, 1),
        "home_ppda": round(away_passes / h_def_actions, 1),
        "away_ppda": round(home_passes / a_def_actions, 1),
    }

@app.get("/api/matches/{match_id}/events")
def get_match_events(match_id: int, db: Session = Depends(get_db)):
    events = db.query(Event).filter(Event.match_id == match_id).all()
    res = []
    for e in events:
        res.append({
            "id": e.id,
            "minute": e.minute,
            "team": e.team.name,
            "player": e.player.name if e.player else "Unknown",
            "type": e.type_name,
            "outcome": e.outcome,
            "x": e.x,
            "y": e.y,
            "end_x": e.end_x,
            "end_y": e.end_y,
            "xg": e.xg,
            "xt": e.xt,
            "is_shot": e.is_shot,
            "is_big_chance": e.is_big_chance,
            "is_penalty": e.is_penalty,
            "is_final_third_pass": e.is_final_third_pass,
            "is_progressive_pass": e.is_progressive_pass
        })
    return res

@app.get("/api/matches/{match_id}/momentum")
def get_match_momentum(match_id: int, db: Session = Depends(get_db)):
    """ Returns cumulative xT and xG per minute for danger level graph """
    events = db.query(Event).filter(Event.match_id == match_id, Event.minute <= 100).order_by(Event.minute).all()
    
    home_id = db.query(Match).filter(Match.id == match_id).first().home_team_id
    
    minutes = list(range(0, 100))
    home_danger = [0.0] * 100
    away_danger = [0.0] * 100
    
    for e in events:
        min_idx = e.minute if e.minute < 100 else 99
        val = (e.xg or 0) * 5 + (e.xt or 0) # Rough danger formula
        if e.team_id == home_id:
            home_danger[min_idx] += val
        else:
            away_danger[min_idx] += val
            
    return {
        "minutes": minutes,
        "home_danger": home_danger,
        "away_danger": away_danger
    }

@app.get("/api/matches/{match_id}/pass-network")
def get_pass_network(match_id: int, team: str = None, progressive_only: bool = False, db: Session = Depends(get_db)):
    """ Returns nodes (players) and edges (passes) for D3.js """
    match = db.query(Match).filter(Match.id == match_id).first()
    target_team_id = match.home_team_id
    if team and team.lower() == match.away_team.name.lower():
        target_team_id = match.away_team_id
        
    events = db.query(Event).filter(Event.match_id == match_id, Event.team_id == target_team_id, Event.type_name == "Pass", Event.outcome == "Successful").all()
    
    # Calculate average positions and total touches (passes)
    players = {}
    edges_dict = {}
    
    for i, e in enumerate(events):
        if not e.player: continue
        p_name = e.player.name
        
        if p_name not in players:
            players[p_name] = {"id": p_name, "x_sum": 0, "y_sum": 0, "count": 0}
            
        players[p_name]["x_sum"] += e.x
        players[p_name]["y_sum"] += e.y
        players[p_name]["count"] += 1
        
        # Look for receiver (next pass by same team usually)
        if i + 1 < len(events):
            next_e = events[i+1]
            if next_e.player:
                receiver = next_e.player.name
                
                # Apply filter for D3 edges if progressive_only is true
                if progressive_only and not e.is_progressive_pass:
                    continue
                    
                edge_id = f"{p_name}-{receiver}"
                if edge_id not in edges_dict:
                    edges_dict[edge_id] = {"source": p_name, "target": receiver, "value": 0, "xt": 0}
                edges_dict[edge_id]["value"] += 1
                edges_dict[edge_id]["xt"] += e.xt or 0
                
    nodes = []
    for p in players.values():
        nodes.append({
            "id": p["id"],
            "x": p["x_sum"] / p["count"],
            "y": p["y_sum"] / p["count"],
            "touches": p["count"]
        })
        
    edges = [e for e in edges_dict.values() if e["value"] > 2] # Filter noise
    
    return {"nodes": nodes, "links": edges}

@app.get("/api/tactics/zones")
def get_zonal_dominance(match_id: int, db: Session = Depends(get_db)):
    """ Divides pitch into 5x6 grid and returns possession breakdown per zone """
    # Real grid calculation would aggregate x/y coords.
    # We will do a simple mapping. X ranges 0-100, Y ranges 0-100.
    # 6 columns in X (16.6 width). 5 rows in Y (20 height).
    grid = [[{"home": 0, "away": 0} for _ in range(6)] for _ in range(5)]
    events = db.query(Event).filter(Event.match_id == match_id, Event.type_name=="Pass").all()
    
    match = db.query(Match).filter(Match.id == match_id).first()
    hid = match.home_team_id
    
    for e in events:
        if e.x is None or e.y is None: continue
        col = min(5, int(e.x / 16.66))
        row = min(4, int(e.y / 20.0))
        
        if e.team_id == hid:
            grid[row][col]["home"] += 1
        else:
            grid[row][col]["away"] += 1
            
    # Calculate dominance percentage (-1 to 1) for color mapping
    dominance = []
    for r in range(5):
        dom_row = []
        for c in range(6):
            h = grid[r][c]["home"]
            a = grid[r][c]["away"]
            tot = h + a
            if tot == 0:
                dom_row.append(0)
            else:
                dom_row.append(round((h - a) / tot, 2))
        dominance.append(dom_row)
        
    return dominance

@app.get("/api/season/leaderboard")
def get_season_leaderboard(db: Session = Depends(get_db)):
    """ Aggregate season stats across all matches """
    from sqlalchemy import func, Integer
    stats = db.query(
        Player.name,
        Team.name.label("team_name"),
        func.sum(Event.xg).label("total_xg"),
        func.sum(Event.xt).label("total_xt"),
        func.sum(func.cast(Event.is_progressive_pass, Integer)).label("prog_passes")
    ).join(Player, Event.player_id == Player.id)\
     .join(Team, Player.team_id == Team.id)\
     .group_by(Player.id)\
     .having(func.sum(Event.xt) > 0)\
     .order_by(func.sum(Event.xt).desc())\
     .limit(100).all()
     
    res = []
    for s in stats:
        res.append({
            "player": s.name,
            "team": s.team_name,
            "xg": round(s.total_xg or 0, 2),
            "xt": round(s.total_xt or 0, 3),
            "prog_passes": s.prog_passes or 0
        })
    return res
