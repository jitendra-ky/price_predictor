from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField

User = get_user_model()

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="predictions")
    ticker = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField()
    plot_urls = models.JSONField()
    
    def __str__(self):
        return f"{self.ticker} {self.created}"
    