import math

def calculate_xg(x_ws, y_ws, is_penalty=False, is_big_chance=False, body_part="Unknown"):
    """
    Calculates expected goals for a shot using WhoScored coordinates (0-100 x 0-100).
    Penalties are fixed at 0.76. Big chances get a massive multiplier.
    Aligns with the 'True' formula from shotmap_whoscored.py.
    """
    if is_penalty:
        return 0.76

    # Piecewise-linear WhoScored x → StatsBomb x using calibration points
    if x_ws <= 50:
        x_sb = x_ws * (60.0 / 50.0)
    elif x_ws <= 89:
        x_sb = 60.0 + (x_ws - 50) * (48.0 / 39.0)
    else:
        x_sb = 108.0 + (x_ws - 89) * (12.0 / 11.0)

    # 0.80 multiplier on the Y axis
    y_sb = 80 - y_ws * 0.80
    
    goal_x, goal_y = 120.0, 40.0
    dx = goal_x - x_sb
    dy = goal_y - y_sb
    distance = max(math.sqrt(dx**2 + dy**2), 0.5)
    
    half_goal = 4.0
    angle = math.atan2(half_goal, distance)
    
    # Base geometry xG (matching shotmap_whoscored)
    base_xg = (angle / (math.pi / 2)) * (1 / (1 + distance / 30))
    
    if body_part == "Header":
        base_xg *= 0.4
        
    if is_big_chance:
        base_xg = max(0.35, base_xg * 3.5)
        base_xg = min(0.65, base_xg)
        
    if distance > 18:
        base_xg *= (18 / distance)**2
        
    return round(min(max(base_xg, 0.01), 0.95), 3)

def calculate_xt(x_start, y_start, x_end, y_end):
    """
    Placeholder for grid-based Expected Threat (xT) calculation.
    Values passes/carries based on movement toward higher probability zones.
    """
    # Simple linear approximation: move closer to goal center (100, 50) in WhoScored coords
    dist_start = math.sqrt((100 - x_start)**2 + (50 - y_start)**2)
    dist_end = math.sqrt((100 - x_end)**2 + (50 - y_end)**2)
    
    # If moved closer to goal, positive xT
    reduction = dist_start - dist_end
    
    if reduction > 0 and x_end > 60:
        # Give higher weight to actions ending in final third
        return round((reduction / 100) * 0.15, 4)
    return 0.0
