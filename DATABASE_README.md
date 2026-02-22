# Elite Analytics Database Structure

The `elite_analytics.db` SQLite database serves as the core storage engine for match event data, players, and team information. It allows for efficient querying and generation of advanced analytics visualizations like pass networks, shot maps, and xG models.

## Location
`EliteAnalytics/data/elite_analytics.db`

## Schema Overview

The database consists of four main relational tables:
1. **`teams`**: Stores unique team identities.
2. **`matches`**: Stores high-level match metadata and results.
3. **`players`**: Stores player details linked to specific teams.
4. **`events`**: The core fact table containing chronologically ordered play-by-play actions (passes, shots, dribbles, etc.) with coordinates and expected metrics.

---

### 1. `teams` Table
Stores the unique teams involved in the matches.
* `id` (INTEGER, Primary Key): Unique identifier for the team (often maps to provider IDs like WhoScored).
* `name` (VARCHAR, Unique): The name of the team (e.g., "Barcelona", "Atletico Madrid").

### 2. `matches` Table
Contains the metadata and final scoreline for each scraped fixture.
* `id` (INTEGER, Primary Key): Unique match ID matching the provider (e.g., `1968936`).
* `date` (VARCHAR): The date and time of the fixture.
* `competition` (VARCHAR): The competition name (e.g., "La Liga", "Copa del Rey").
* `home_team_id` (INTEGER, Foreign Key): Links to `teams.id`.
* `away_team_id` (INTEGER, Foreign Key): Links to `teams.id`.
* `home_score` (INTEGER): Final goals scored by the home team.
* `away_score` (INTEGER): Final goals scored by the away team.

### 3. `players` Table
Maintains the roster of players associated with teams.
* `id` (INTEGER, Primary Key): Unique player ID.
* `name` (VARCHAR): The player's full name.
* `position` (VARCHAR): The player's primary position (if available).
* `team_id` (INTEGER, Foreign Key): Links to `teams.id`.

### 4. `events` Table
This is the most critical and granular table in the database. It stores every registered on-ball action in a match.
* `id` (INTEGER, Primary Key): Auto-incrementing internal ID.
* `match_id` (INTEGER, Foreign Key): Links to `matches.id`.
* `team_id` (INTEGER, Foreign Key): Linked team performing the action.
* `player_id` (INTEGER, Foreign Key): Linked player performing the action.
* `event_id` (INTEGER): Provider-specific event identifier to ensure chronological ordering.
* `minute` (INTEGER): The minute the event occurred.
* `second` (INTEGER): The second the event occurred.
* `type_name` (VARCHAR): The classification of the event (e.g., "Pass", "TakeOn", "Shot", "SubstitutionOn").
* `outcome` (VARCHAR): The result of the action (e.g., "Successful", "Unsuccessful").
* `x` (FLOAT): The starting X coordinate of the action (0-100 scale, usually transformed to StatsBomb 120 scale later).
* `y` (FLOAT): The starting Y coordinate of the action.
* `end_x` (FLOAT): The ending X coordinate (for passes/carries).
* `end_y` (FLOAT): The ending Y coordinate.
* `is_shot` (BOOLEAN): Flag if the event is a shot.
* `xg` (FLOAT): The Expected Goals value (if applicable/calculated).
* `xt` (FLOAT): Expected Threat (if calculated).
* `under_pressure` (BOOLEAN): Flag if the action was performed under defensive pressure.
* `is_big_chance` (BOOLEAN): Flag denoting high-value opportunities.
* `is_penalty` (BOOLEAN): Flag if the event is a penalty kick.
* `is_final_third_pass` (BOOLEAN): Flag indicating passes entering the attacking third.
* `is_progressive_pass` (BOOLEAN): Flag for passes moving significantly closer to the opponent's goal.
* `possession_chain_id` (INTEGER): ID clustering sequential events belonging to the same unbroken team possession.
* `qualifiers` (JSON): A stored JSON string containing supplementary flags (e.g., body part used, pass height, set piece context).

## Relationships
- A `team` can have many `players` and partake in many `matches`.
- A `match` contains thousands of `events`.
- An `event` is strictly tied to one `match`, one `team`, and usually one `player`.

## Usage
Data from this database is queried by Python scripts (like `generate_all_assets.py`) using `pandas.read_sql` to filter by `match_id` and `type_name` (e.g., Pass, Shot) to compute aggregate statistics and plot coordinates on a pitch.
