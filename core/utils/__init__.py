from django.core.cache import cache
from django.conf import settings
from datetime import datetime, timedelta
import pytz


def check_rate_limit(key, limit=None, window_minutes=60):
    """
    Check if the rate limit is exceeded for a given key.
    
    Args:
        key: Unique identifier for the rate limit (e.g., user_id, chat_id)
        limit: Number of requests allowed per window (defaults to PREDICT_PER_MIN setting)
        window_minutes: Time window in minutes
    
    Returns:
        tuple: (is_allowed, remaining_requests, reset_time)
    """
    if limit is None:
        limit = settings.PREDICT_PER_MIN
        
    cache_key = f"rate_limit:{key}"
    ist_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist_tz)
    
    # Get current request data
    request_data = cache.get(cache_key, [])
    
    # Convert string timestamps back to datetime objects if needed
    if request_data and isinstance(request_data[0], str):
        request_data = [datetime.fromisoformat(req_time).replace(tzinfo=ist_tz) if datetime.fromisoformat(req_time).tzinfo is None else datetime.fromisoformat(req_time) for req_time in request_data]
    
    # Remove old requests outside the window
    window_start = now - timedelta(minutes=window_minutes)
    request_data = [req_time for req_time in request_data if req_time > window_start]
    
    # Check if limit is exceeded
    if len(request_data) >= limit:
        oldest_request = min(request_data)
        reset_time = oldest_request + timedelta(minutes=window_minutes)
        return False, 0, reset_time
    
    # Add current request
    request_data.append(now)
    
    # Convert datetime objects to ISO strings for cache storage
    request_data_str = [req_time.isoformat() for req_time in request_data]
    
    # Update cache (expire after window duration)
    cache.set(cache_key, request_data_str, timeout=int(window_minutes * 60))
    
    remaining = limit - len(request_data)
    return True, remaining, None