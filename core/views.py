from django.views import View
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Prediction
from .serializers import PredictionSerializer
from .services.predictor import StockPredictor
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from .services.stripe_service import StripeService
import json
import logging

logger = logging.getLogger(__name__)

class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"}, status=200)


class PredictView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        ticker = request.data.get("ticker")
        if not ticker:
            return Response({"error": "Ticker is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Increment prediction count (quota already checked by middleware)
        if hasattr(request.user, 'userprofile'):
            request.user.userprofile.increment_prediction_count()
        
        try:
            predictor = StockPredictor(ticker)
            result = predictor.run()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Save the prediction to the database
        prediction = Prediction.objects.create(
            user = request.user,
            ticker = result['ticker'],
            metrics = {
                "next_day_price": result["next_day_price"],
                "mse": result["mse"],
                "rmse": result["rmse"],
                "r2": result["r2"],
            },
            plot_urls = result["plot_urls"]
        )
        
        serializer = PredictionSerializer(prediction)
        
        # Add quota information to response
        response_data = serializer.data
        if hasattr(request.user, 'userprofile'):
            profile = request.user.userprofile
            response_data['quota'] = {
                'remaining': profile.get_remaining_predictions(),
                'limit': profile.get_daily_quota(),
                'is_pro': profile.is_pro
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)

class PredictionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        prediction = Prediction.objects.filter(user=request.user).order_by('-created')
        serializer = PredictionSerializer(prediction, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user subscription status and quota information"""
        if not hasattr(request.user, 'userprofile'):
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        profile = request.user.userprofile
        
        return Response({
            "user": {
                "username": request.user.username,
                "email": request.user.email,
                "is_pro": profile.is_pro,
            },
            "quota": {
                "remaining": profile.get_remaining_predictions(),
                "limit": profile.get_daily_quota(),
                "used_today": profile.daily_predictions_count if profile.last_prediction_date == profile.last_prediction_date else 0,
            },
            "subscription": {
                "tier": "Pro" if profile.is_pro else "Free",
                "features": {
                    "daily_predictions": "Unlimited" if profile.is_pro else "5",
                    "priority_queue": profile.is_pro,
                    "telegram_unlimited": profile.is_pro,
                }
            }
        })

class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create Stripe checkout session for subscription"""
        try:
            # Check if user is already Pro
            if hasattr(request.user, 'userprofile') and request.user.userprofile.is_pro:
                return Response(
                    {"error": "You are already a Pro subscriber"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build URLs
            base_url = settings.BASE_URL
            success_url = f"{base_url}/dashboard/?subscription=success"
            cancel_url = f"{base_url}/dashboard/?subscription=cancel"
            
            # Create checkout session
            session = StripeService.create_checkout_session(
                user=request.user,
                success_url=success_url,
                cancel_url=cancel_url
            )
            
            return Response({
                "checkout_url": session.url,
                "session_id": session.id
            })
            
        except Exception as e:
            logger.error(f"Error creating checkout session for user {request.user.username}: {e}")
            return Response(
                {"error": "Failed to create checkout session"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload in Stripe webhook: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in Stripe webhook: {e}")
        return HttpResponse(status=400)
    
    logger.info(f"Received Stripe webhook event: {event['type']}")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Retrieve the subscription
        if session.mode == 'subscription':
            subscription_id = session.subscription
            subscription = stripe.Subscription.retrieve(subscription_id)
            StripeService.handle_subscription_created(subscription)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        StripeService.handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        StripeService.handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_succeeded':
        # Handle successful payment (renewal)
        invoice = event['data']['object']
        if invoice.subscription:
            subscription = stripe.Subscription.retrieve(invoice.subscription)
            StripeService.handle_subscription_updated(subscription)
    
    elif event['type'] == 'invoice.payment_failed':
        # Handle failed payment
        invoice = event['data']['object']
        logger.warning(f"Payment failed for subscription: {invoice.subscription}")
    
    else:
        logger.info(f"Unhandled Stripe event type: {event['type']}")
    
    return HttpResponse(status=200)