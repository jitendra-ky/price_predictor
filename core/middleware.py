"""
Middleware for handling quota enforcement and other request processing
"""
from django.http import JsonResponse
from django.urls import resolve
from django.contrib.auth.models import AnonymousUser


class QuotaMiddleware:
    """
    Middleware to enforce daily prediction quotas for users
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Endpoints that require quota checking
        self.quota_endpoints = [
            'predict',  # core.urls predict endpoint
        ]
    
    def __call__(self, request):
        # Check quota before processing prediction requests
        if self.should_check_quota(request):
            quota_response = self.check_quota(request)
            if quota_response:
                return quota_response
        
        response = self.get_response(request)
        
        # Add quota info to response headers for API endpoints
        if self.is_api_endpoint(request) and hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            if hasattr(request.user, 'userprofile'):
                profile = request.user.userprofile
                response['X-Quota-Remaining'] = str(profile.get_remaining_predictions())
                response['X-Quota-Limit'] = str(profile.get_daily_quota())
                response['X-Is-Pro'] = str(profile.is_pro).lower()
        
        return response
    
    def should_check_quota(self, request):
        """
        Determine if this request should be subject to quota checking
        """
        if request.method != 'POST':
            return False
        
        try:
            resolved = resolve(request.path_info)
            return resolved.url_name in self.quota_endpoints
        except:
            return False
    
    def is_api_endpoint(self, request):
        """
        Check if this is an API endpoint
        """
        return request.path_info.startswith('/api/')
    
    def check_quota(self, request):
        """
        Check if user has exceeded their daily quota
        Returns JsonResponse if quota exceeded, None otherwise
        """
        if isinstance(request.user, AnonymousUser):
            return JsonResponse(
                {"error": "Authentication required"}, 
                status=401
            )
        
        if not hasattr(request.user, 'userprofile'):
            return JsonResponse(
                {"error": "User profile not found"}, 
                status=500
            )
        
        profile = request.user.userprofile
        
        if not profile.can_make_prediction():
            return JsonResponse(
                {
                    "error": "Daily prediction quota exceeded",
                    "message": "You have reached your daily limit of 5 predictions. Upgrade to Pro for unlimited predictions.",
                    "quota": {
                        "remaining": 0,
                        "limit": 5,
                        "is_pro": False
                    },
                    "upgrade_required": True
                }, 
                status=429
            )
        
        return None
