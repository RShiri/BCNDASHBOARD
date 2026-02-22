import soccerdata as sd
import sys

def get_bcn_ids():
    match_ids = []
    
    try:
        ws_liga = sd.WhoScored(leagues="ESP-La Liga", seasons="2526")
        sched = ws_liga.read_schedule().reset_index()
        barca_liga = sched[(sched['home_team'].str.contains('Barcelona', na=False)) | (sched['away_team'].str.contains('Barcelona', na=False))]
        print("La Liga Matches:")
        print(barca_liga[['game_id', 'date', 'home_team', 'away_team', 'score']])
        match_ids.extend(barca_liga['game_id'].tolist())
    except Exception as e:
        print("Error fetching La Liga 25/26:", e)

    try:
        ws_cl = sd.WhoScored(leagues="INT-Champions League", seasons="2526")
        sched_cl = ws_cl.read_schedule().reset_index()
        barca_cl = sched_cl[(sched_cl['home_team'].str.contains('Barcelona', na=False)) | (sched_cl['away_team'].str.contains('Barcelona', na=False))]
        print("\nChampions League Matches:")
        print(barca_cl[['game_id', 'date', 'home_team', 'away_team', 'score']])
        match_ids.extend(barca_cl['game_id'].tolist())
    except Exception as e:
        print("Error fetching UCL 25/26:", e)

    print("\nCombined True IDs:")
    print(match_ids)
    
if __name__ == "__main__":
    get_bcn_ids()
