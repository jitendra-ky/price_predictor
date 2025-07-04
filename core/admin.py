from django.contrib import admin
from .models import Prediction, TelegramProfile

admin.site.register(Prediction)
admin.site.register(TelegramProfile)