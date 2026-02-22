from statsbombpy import sb
import pandas as pd

def load_match_data(match_id):
    """
    Fetches match events using statsbombpy.
    
    Args:
        match_id (int): The StatsBomb match ID.
        
    Returns:
        tuple: (events_df, match_metadata)
    """
    try:
        # Fetch events
        events = sb.events(match_id=match_id)
        
        # Helper to extract x, y if they are in a specific column like 'location'
        # StatsBomb data usually has a 'location' column with [x, y] lists
        if 'location' in events.columns:
            events[['x', 'y']] = pd.DataFrame(events['location'].tolist(), index=events.index)
        
        # Extract pass end locations
        if 'pass_end_location' in events.columns:
             events[['pass_end_x', 'pass_end_y']] = pd.DataFrame(events['pass_end_location'].tolist(), index=events.index)
             
        return events
    except Exception as e:
        print(f"Error fetching data for match {match_id}: {e}")
        return pd.DataFrame()

def get_team_names(events):
    """
    Extracts home and away team names from events.
    """
    if events.empty:
        return "Home Team", "Away Team"
    
    # Assuming the first two unique teams are the ones playing
    teams = events['team'].unique()
    if len(teams) >= 2:
        return teams[0], teams[1]
    return "Home Team", "Away Team"
