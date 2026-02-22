import json
import os
from sqlalchemy.orm import Session
from EliteAnalytics.backend.database import engine, Match, Team, Player, Event, Base
from EliteAnalytics.backend.metrics import calculate_xg, calculate_xt

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(_ROOT, "assets", "data")

def parse_match_data(session: Session, json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 1. Teams
    home_data = data.get("home", {})
    away_data = data.get("away", {})
    
    def get_or_create_team(t_id, t_name):
        team = session.query(Team).filter_by(id=t_id).first()
        if not team:
            team = Team(id=t_id, name=t_name)
            session.add(team)
        return team

    home_team = get_or_create_team(home_data.get("teamId"), home_data.get("name"))
    away_team = get_or_create_team(away_data.get("teamId"), away_data.get("name"))
    session.commit()
    
    # 2. Match
    filename = os.path.basename(json_path)
    real_match_id = int(filename.split("_")[1]) if "_" in filename else data.get("matchId")
    
    match = session.query(Match).filter_by(id=real_match_id).first()
    if not match:
        match = Match(
            id=real_match_id,
            date=data.get("startDate", "2026-02-16T20:00:00Z"),
            competition="La Liga/UCL",
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=0, # Will compute later
            away_score=0
        )
        session.add(match)
        session.commit()
        
    # 3. Players Mapping (Find all seen players in events or lineups if available)
    # We will just create players on the fly as we process events, but a quick pass is better.
    players_dict = data.get("playerIdNameDictionary", {})
    # Need to know which team a player belongs to. We can infer from events.
    player_teams = {}
    for ev in data.get("events", []):
        pid = ev.get("playerId")
        tid = ev.get("teamId")
        if pid and tid:
            player_teams[pid] = tid
            
    for pid, p_name in players_dict.items():
        pid = int(pid)
        player = session.query(Player).filter_by(id=pid).first()
        if not player:
            tid = player_teams.get(pid, home_team.id) # default to home if missing
            player = Player(id=pid, name=p_name, team_id=tid)
            session.add(player)
    session.commit()
    
    # 4. Events & Sequences
    events_raw = data.get("events", [])
    
    current_chain_id = 1
    current_team_possession = None
    
    home_goals = 0
    away_goals = 0
    
    for i, ev in enumerate(events_raw):
        ev_type = ev.get("type", {}).get("displayName", "Unknown")
        ev_outcome = ev.get("outcomeType", {}).get("displayName", "Successful")
        team_id = ev.get("teamId")
        player_id = ev.get("playerId")
        
        # Determine Sequence (Possession Chain)
        # Change chain if team changes or play stops (e.g. ball out, foul)
        if team_id != current_team_possession and ev_outcome == "Successful":
            if ev_type in ["Pass", "TakeOn", "Clearance", "Recovery", "Interception"]:
                current_team_possession = team_id
                current_chain_id += 1
                
        # Qualifiers parsing
        quals = {q.get("type", {}).get("displayName", ""): q for q in ev.get("qualifiers", [])}
        
        is_shot = ev_type in ["MissedShots", "SavedShot", "ShotOnPost", "Goal"]
        if is_shot and ev_type == "Goal":
            if team_id == home_team.id: home_goals += 1
            if team_id == away_team.id: away_goals += 1
            
        under_pressure = "UnderPressure" in quals
        is_big_chance = "BigChance" in quals
        is_penalty = ev_type == "Goal" and "Penalty" in quals or "Penalty" in quals
        
        body_part = "Foot"
        if "Head" in quals: body_part = "Header"
        if "RightFoot" in quals: body_part = "Right Foot"
        if "LeftFoot" in quals: body_part = "Left Foot"

        x = ev.get("x")
        y = ev.get("y")
        end_x = None
        end_y = None
        for q in ev.get("qualifiers", []):
            if q.get("type", {}).get("displayName") == "PassEndX":
                end_x = float(q.get("value", 0))
            if q.get("type", {}).get("displayName") == "PassEndY":
                end_y = float(q.get("value", 0))
                
        # Metrics Calculation
        xg = None
        xt = None
        is_final_third_pass = False
        is_progressive_pass = False
        
        if is_shot and x is not None and y is not None:
            xg = calculate_xg(float(x), float(y), is_penalty, is_big_chance, body_part)
            
        if ev_type == "Pass" and ev_outcome == "Successful" and x is not None and y is not None and end_x is not None and end_y is not None:
            xt = calculate_xt(float(x), float(y), float(end_x), float(end_y))
            
            # Map coordinates to 120x80 scale
            sx = float(x) * 1.20
            sy = 80 - float(y) * 0.80
            s_end_x = float(end_x) * 1.20
            
            # Category 2: Final Third Pass (ends in attacking 25%, > 80/120)
            if s_end_x > 80.0:
                is_final_third_pass = True
                
            # Category 3: Progressive Pass
            # 1. Originates outside own 40% (x >= 48)
            if sx >= 48.0:
                distance_forward = s_end_x - sx
                # 2. Distance threshold based on origin
                if sx < 60.0:
                    if distance_forward >= 30.0: is_progressive_pass = True
                elif sx < 90.0:
                    if distance_forward >= 15.0: is_progressive_pass = True
                else:
                    if distance_forward >= 10.0: is_progressive_pass = True

        db_event = Event(
            match_id=match.id,
            team_id=team_id,
            player_id=player_id,
            event_id=ev.get("eventId") or ev.get("id"),
            minute=ev.get("minute"),
            second=ev.get("second"),
            type_name=ev_type,
            outcome=ev_outcome,
            x=x,
            y=y,
            end_x=end_x,
            end_y=end_y,
            is_shot=is_shot,
            xg=xg,
            xt=xt,
            under_pressure=under_pressure,
            is_big_chance=is_big_chance,
            is_penalty=is_penalty,
            is_final_third_pass=is_final_third_pass,
            is_progressive_pass=is_progressive_pass,
            possession_chain_id=current_chain_id,
            qualifiers=ev.get("qualifiers")
        )
        session.add(db_event)
        
    match.home_score = home_goals
    match.away_score = away_goals
    session.commit()
    
    print(f"Match {match.id} loaded successfully. Found {len(events_raw)} events.")


def main():
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    
    if not os.path.exists(DATA_DIR):
        print(f"Data directory not found: {DATA_DIR}")
        session.close()
        return
        
    match_files = [f for f in os.listdir(DATA_DIR) if f.startswith("match_") and f.endswith("_cache.json")]
    
    if not match_files:
        print(f"No match cache files found in {DATA_DIR}")
    else:
        for filename in match_files:
            file_path = os.path.join(DATA_DIR, filename)
            try:
                print(f"Parsing {filename}...")
                parse_match_data(session, file_path)
            except Exception as e:
                print(f"Error parsing {filename}: {e}")
                session.rollback()

    session.close()

if __name__ == "__main__":
    main()
