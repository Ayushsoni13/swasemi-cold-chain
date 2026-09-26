from datetime import datetime, timezone
from typing import Optional

def compute_tracker_status(last_seen: Optional[datetime]) -> str:
    """
    Computes tracker status based on last_seen timestamp:
    - ONLINE: last_seen <= 30 seconds ago
    - DELAYED: 30 seconds < last_seen <= 120 seconds ago
    - OFFLINE: last_seen > 120 seconds ago or None
    """
    if not last_seen:
        return "OFFLINE"
        
    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
        
    delta_seconds = (now - last_seen).total_seconds()
    
    if delta_seconds <= 30.0:
        return "ONLINE"
    elif delta_seconds <= 120.0:
        return "DELAYED"
    else:
        return "OFFLINE"
