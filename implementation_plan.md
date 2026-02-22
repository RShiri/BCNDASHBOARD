# Match Dashboard Implementation Plan: FC Barcelona vs Athletic Club (5-0)

## Goal
Create a comprehensive match dashboard visualization for the recent 5-0 victory of FC Barcelona against Athletic Club (Jan 7, 2026). The dashboard will include Passing Networks, a Stats Table, and Shot Maps.

## User Review Required
> [!IMPORTANT]
> **Data Accessibility**: Detailed "Passing Network" data (X, Y coordinates for every pass) is notoriously difficult to scrape from public endpoints (FotMob/WhoScored) without blocking. 
> **Strategy**: I will attempt to fetch detailed event data. If full pass coordinates are unavailable, I will fallback to a "Heatmap" or "Zone Map" visualization for the middle section as per instructions, while retaining the Shot Map and Stats which are more accessible.

## Proposed Changes

### Script Generation
I will create a single Python script `project_1_match_dashboard.py` in the `Projects` folder (or root) to execute the task.

1.  **Data Acquisition (`get_match_data`)**:
    *   **Source**: FotMob API (via `cloudscraper`) is preferred for reliability over Selenium.
    *   **Match Identification**: Search logic to find the specific match ID for "Barcelona" vs "Athletic Club" on "2026-01-08" (or surrounding dates).
    *   **Payloads**:
        *   `matchDetails`: General stats, Shotmap.
        *   `matchEvents` (if accessible): For passing network. 
        *   *Fallback*: If direct scraping fails, `soccerdata` library might be used if configured for the 2026 season.

2.  **Visualization (`create_dashboard`)**:
    *   **Framework**: `matplotlib` with `mplsoccer`.
    *   **Layout**:
        *   **Header**: Logos and Scoreline.
        *   **Row 1**: Passing Networks (Left: Barca, Right: Athletic).
        *   **Row 2**: Stats Comparison Table.
        *   **Row 3**: Shot Maps (Left: Barca, Right: Athletic).
    *   **Styling**: Dark/Night mode (`pitch_color='#1c2833'`, `text_color='white'`).

### Files to Create
#### [NEW] [project_1_match_dashboard.py](file:///c:/Users/puzik/OneDrive/%D7%A9%D7%95%D7%9C%D7%97%D7%9F%20%D7%94%D7%A2%D7%91%D7%95%D7%93%D7%94/BCNPROJECT-main/Projects/project_1_match_dashboard.py)

## Verification Plan
### Automated Tests
*   Run the script: `python Projects/project_1_match_dashboard.py` in the terminal.
*   Success Criteria:
    *   Script runs without error.
    *   Match ID is successfully resolved.
    *   Data is scraped (printed summary).
    *   Values (5-0 score, correct teams) match.
    *   `match_dashboard.png` is generated.

### Manual Verification
*   Inspect the generated image `match_dashboard.png` for layout correctness and data accuracy (Score 5-0, Shot locations plausible).
