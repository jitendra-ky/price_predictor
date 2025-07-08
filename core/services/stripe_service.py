"""
Stripe service for handling subscription payments
"""
import stripe
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from core.models import Subscription
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for Stripe integration"""
    
    @staticmethod
    def create_checkout_session(user, success_url, cancel_url):
        """
        Create a Stripe Checkout session for subscription
        """
        try:
            # Create or get Stripe customer
            customer_id = StripeService.get_or_create_customer(user)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user.id,
                }
            )
            
            logger.info(f"Created Stripe checkout session {session.id} for user {user.username}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating Stripe checkout session for user {user.username}: {e}")
            raise e
    
    @staticmethod
    def get_or_create_customer(user):
        """
        Get or create a Stripe customer for the user
        """
        try:
            # Check if user already has a customer ID in existing subscriptions
            existing_subscription = Subscription.objects.filter(user=user).first()
            if existing_subscription and existing_subscription.stripe_customer_id:
                return existing_subscription.stripe_customer_id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={
                    'user_id': user.id,
                }
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.username}")
            return customer.id
            
        except Exception as e:
            logger.error(f"Error creating Stripe customer for user {user.username}: {e}")
            raise e
    
    @staticmethod
    def handle_subscription_created(stripe_subscription):
        """
        Handle subscription created event from Stripe webhook
        """
        try:
            user_id = stripe_subscription.metadata.get('user_id')
            if not user_id:
                # Try to get user from customer metadata
                customer = stripe.Customer.retrieve(stripe_subscription.customer)
                user_id = customer.metadata.get('user_id')
            
            if not user_id:
                logger.error(f"No user_id found in subscription metadata: {stripe_subscription.id}")
                return False
            
            user = User.objects.get(id=user_id)
            
            # Create or update subscription record
            subscription, created = Subscription.objects.update_or_create(
                stripe_subscription_id=stripe_subscription.id,
                defaults={
                    'user': user,
                    'stripe_customer_id': stripe_subscription.customer,
                    'status': stripe_subscription.status,
                    'current_period_start': datetime.fromtimestamp(
                        stripe_subscription.current_period_start, tz=timezone.utc
                    ),
                    'current_period_end': datetime.fromtimestamp(
                        stripe_subscription.current_period_end, tz=timezone.utc
                    ),
                }
            )
            
            # Update user profile pro status
            if hasattr(user, 'userprofile'):
                user.userprofile.update_pro_status()
            
            logger.info(f"{'Created' if created else 'Updated'} subscription {subscription.id} for user {user.username}")
            return True
            
        except User.DoesNotExist:
            logger.error(f"User not found for subscription {stripe_subscription.id}")
            return False
        except Exception as e:
            logger.error(f"Error handling subscription created: {e}")
            return False
    
    @staticmethod
    def handle_subscription_updated(stripe_subscription):
        """
        Handle subscription updated event from Stripe webhook
        """
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription.id
            )
            
            # Update subscription status and dates
            subscription.status = stripe_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_subscription.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_subscription.current_period_end, tz=timezone.utc
            )
            subscription.save()
            
            # Update user profile pro status
            if hasattr(subscription.user, 'userprofile'):
                subscription.user.userprofile.update_pro_status()
            
            logger.info(f"Updated subscription {subscription.id} for user {subscription.user.username}")
            return True
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe subscription {stripe_subscription.id}")
            return False
        except Exception as e:
            logger.error(f"Error handling subscription updated: {e}")
            return False
    
    @staticmethod
    def handle_subscription_deleted(stripe_subscription):
        """
        Handle subscription deleted/canceled event from Stripe webhook
        """
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription.id
            )
            
            # Update subscription status
            subscription.status = 'canceled'
            subscription.save()
            
            # Update user profile pro status
            if hasattr(subscription.user, 'userprofile'):
                subscription.user.userprofile.update_pro_status()
            
            logger.info(f"Canceled subscription {subscription.id} for user {subscription.user.username}")
            return True
            
        except Subscription.DoesNotExist:
            logger.error(f"Subscription not found for Stripe subscription {stripe_subscription.id}")
            return False
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {e}")
            return False
