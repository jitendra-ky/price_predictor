from django.core.cache import cache
import time

def is_rate_limited(user_id, action, limit=5, window=3600):
    """
    Simple rate limiter using Django cache.
    
    Args:
        user_id: User identifier
        action: Action type (e.g., 'predict')
        limit: Number of requests allowed (default: 5)
        window: Time window in seconds (default: 3600 = 1 hour)
    
    Returns:
        bool: True if rate limited, False otherwise
    """
    cache_key = f"rate_limit:{action}:{user_id}"
    
    # Get current count and timestamps
    data = cache.get(cache_key, [])
    current_time = time.time()
    
    # Remove old entries outside the window
    data = [timestamp for timestamp in data if current_time - timestamp < window]
    
    # Check if limit exceeded
    if len(data) >= limit:
        return True
    
    # Add current timestamp and save
    data.append(current_time)
    cache.set(cache_key, data, window)
    
    return False
