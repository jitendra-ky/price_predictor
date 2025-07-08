"""
Context processors for adding user subscription information to templates
"""

def user_subscription_context(request):
    """
    Add user subscription information to template context
    """
    context = {
        'user_is_pro': False,
        'user_quota_remaining': 0,
        'user_quota_limit': 5,
    }
    
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        profile = request.user.userprofile
        context.update({
            'user_is_pro': profile.is_pro,
            'user_quota_remaining': profile.get_remaining_predictions(),
            'user_quota_limit': profile.get_daily_quota(),
        })
    
    return context
