from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import date

User = get_user_model()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    is_pro = models.BooleanField(default=False)
    daily_predictions_count = models.IntegerField(default=0)
    last_prediction_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Pro' if self.is_pro else 'Free'}"
    
    def get_daily_quota(self):
        """Return daily prediction quota based on subscription tier"""
        return float('inf') if self.is_pro else 5
    
    def can_make_prediction(self):
        """Check if user can make a prediction today"""
        if self.is_pro:
            return True
        
        today = date.today()
        if self.last_prediction_date != today:
            # Reset count for new day
            self.daily_predictions_count = 0
            self.last_prediction_date = today
            self.save()
        
        return self.daily_predictions_count < 5
    
    def increment_prediction_count(self):
        """Increment daily prediction count"""
        today = date.today()
        if self.last_prediction_date != today:
            self.daily_predictions_count = 0
            self.last_prediction_date = today
        
        self.daily_predictions_count += 1
        self.save()
    
    def get_remaining_predictions(self):
        """Get remaining predictions for today"""
        if self.is_pro:
            return float('inf')
        
        today = date.today()
        if self.last_prediction_date != today:
            return 5
        
        return max(0, 5 - self.daily_predictions_count)
    
    def update_pro_status(self):
        """Update pro status based on active subscription"""
        active_subscription = self.user.subscriptions.filter(
            status__in=['active', 'trialing']
        ).first()
        
        new_status = bool(active_subscription)
        if self.is_pro != new_status:
            self.is_pro = new_status
            self.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="predictions")
    ticker = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField()
    plot_urls = models.JSONField()
    
    def __str__(self):
        return f"{self.ticker} {self.created}"
    
class TelegramProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="telegram_profile")
    chat_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Telegram Profile: {self.user.username}"

class Subscription(models.Model):
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('trialing', 'Trialing'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status in ['active', 'trialing']
