import pandas as pd

def generate_shot_map_data(events_df, team_name):
    """
    Extracts shot data for a specific team.
    
    Args:
        events_df (pd.DataFrame): The DataFrame containing match events.
        team_name (str): The name of the team.
        
    Returns:
        pd.DataFrame: DataFrame with shot details (x, y, outcome, xg, player).
    """
    team_events = events_df[events_df['team'] == team_name].copy()
    shots = team_events[team_events['type'] == 'Shot'].copy()
    
    # Extract relevant columns
    # StatsBomb xG is usually in 'shot_statsbomb_xg'
    xg_col = 'shot_statsbomb_xg' if 'shot_statsbomb_xg' in shots.columns else 'xg' # Fallback
    outcome_col = 'shot_outcome'
    
    # Ensure xG is float and fill NaNs
    if xg_col in shots.columns:
        shots[xg_col] = shots[xg_col].fillna(0).astype(float)
    else:
        shots['xg'] = 0.0

    result = shots[['player', 'x', 'y', outcome_col, xg_col]].copy()
    result.rename(columns={xg_col: 'xg', outcome_col: 'outcome'}, inplace=True)
    
    return result
