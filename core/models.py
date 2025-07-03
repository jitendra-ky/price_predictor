from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

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
