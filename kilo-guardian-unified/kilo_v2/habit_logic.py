"""
habit_logic.py: Rule-based logic for habit/activity analysis and check-in triggers.
All logic is kept here to keep server_core.py clean.
"""

import datetime
from typing import Any, Dict, List

# Example: Each observation is a dict with keys: user, cam, position, on_track, goal, timestamp


def parse_iso(ts: str) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(ts)
    except Exception:
        return datetime.datetime.now()


def get_user_baseline(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate baseline stats for a user: avg sleep, avg sitting, avg movement, etc.
    """
    # For demo, just count positions
    stats = {}
    for obs in observations:
        pos = obs.get("position", "unknown")
        stats[pos] = stats.get(pos, 0) + 1
    return stats


def detect_out_of_norm(
    observations: List[Dict[str, Any]], baseline: Dict[str, Any]
) -> List[str]:
    """
    Return a list of check-in triggers based on recent observations vs. baseline.
    """
    triggers = []
    now = datetime.datetime.now()
    # Example: If user is in bed (lying) > 10 hours in last 24h and not marked as sick
    lying_obs = [o for o in observations if o.get("position") == "lying"]
    lying_recent = [
        o
        for o in lying_obs
        if (now - parse_iso(o["timestamp"])) < datetime.timedelta(hours=24)
    ]
    if len(lying_recent) > 20:  # ~5-min intervals
        triggers.append("User has been in bed for a long time. Check in.")
    # Example: If user is pacing (walking) for > 30 min in last 2h
    walking_obs = [o for o in observations if o.get("position") == "walking"]
    walking_recent = [
        o
        for o in walking_obs
        if (now - parse_iso(o["timestamp"])) < datetime.timedelta(hours=2)
    ]
    if len(walking_recent) > 6:  # >30 min
        triggers.append("User is pacing a lot. Check in.")
    # Add more rules as needed
    return triggers


def snooze_check_in(user_state: Dict[str, Any]) -> bool:
    """
    Returns True if user is in a snoozed state (e.g., marked as sick), else False.
    """
    # For demo, just check a flag
    return user_state.get("snooze", False)


# You can expand this module with more advanced logic or ML in the future.
