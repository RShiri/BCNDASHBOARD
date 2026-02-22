import pandas as pd
import numpy as np

def calculate_passing_network(events_df, team_name, min_passes=3):
    """
    Calculates the average player positions and the number of passes between players.
    
    Args:
        events_df (pd.DataFrame): The DataFrame containing match events.
        team_name (str): The name of the team to calculate the network for.
        min_passes (int): Minimum number of passes to return an edge (connection).
        
    Returns:
        tuple: (average_locations_df, pass_lines_df)
    """
    # Filter for specific team and Pass events
    team_events = events_df[events_df['team'] == team_name].copy()
    passes = team_events[team_events['type'] == 'Pass'].copy()
    
    # Consider only successful passes usually, but for general structure all passes might be okay.
    # Typically passing networks use successful passes.
    if 'pass_outcome' in passes.columns:
         passes = passes[passes['pass_outcome'].isnull()] # Hull is null for successful in statsbombpy usually

    # Group by player to get average locations
    avg_locs = passes.groupby(['player', 'player_id']).agg({'x': ['mean'], 'y': ['mean', 'count']})
    avg_locs.columns = ['x', 'y', 'count']
    avg_locs.reset_index(inplace=True)

    # Calculate passes between players
    pass_between = passes.groupby(['player', 'pass_recipient']).id.count().reset_index()
    pass_between.rename(columns={'id': 'pass_count'}, inplace=True)
    
    # Merge with average locations to get start and end coordinates for the lines
    pass_lines = pass_between.merge(avg_locs[['player', 'x', 'y']], left_on='player', right_on='player')
    pass_lines.rename(columns={'x': 'x_start', 'y': 'y_start'}, inplace=True)
    
    pass_lines = pass_lines.merge(avg_locs[['player', 'x', 'y']], left_on='pass_recipient', right_on='player', suffixes=('', '_end'))
    pass_lines.rename(columns={'x': 'x_end', 'y': 'y_end'}, inplace=True)
    
    # Filter out low pass counts
    pass_lines = pass_lines[pass_lines['pass_count'] >= min_passes]
    
    return avg_locs, pass_lines
