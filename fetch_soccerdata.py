
import soccerdata as sd
import json

# Try initializing for Spanish Super Cup
# Seasons format '2526' likely or start year '2025'
try:
    ws = sd.WhoScored(leagues="ESP-Super Cup", seasons="2526")
    print("Initialized WhoScored scraper.")
    
    # Try reading events for the match date?
    # Usually read_schedule first
    schedule = ws.read_schedule()
    print(schedule.head())
    
    # Filter for our match
    match = schedule[ 
        (schedule['home_team'].str.contains('Barcelona')) & 
        (schedule['away_team'].str.contains('Athletic')) 
    ]
    
    if not match.empty:
        game_id = match.index[0] # assuming index is match_id
        print(f"Found game_id: {game_id}")
        
        events = ws.read_events(match_id=game_id)
        print("Events fetched.")
        
        # Save to JSON for our dashboard script to use
        # events is a DataFrame. Export to CSV or JSON structure.
        events.reset_index().to_json("match_events_ws.json", orient='records')
        print("Saved match_events_ws.json")
    else:
        print("Match not found in schedule.")
        
except Exception as e:
    print(f"Soccerdata Error: {e}")
