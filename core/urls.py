from django.urls import path
from .views import PredictView, PredictionListView, UserStatusView, CreateCheckoutSessionView, stripe_webhook

urlpatterns = [
    path("v1/predict/", PredictView.as_view(), name="predict"),
    path("v1/predictions/", PredictionListView.as_view(), name="predictions"),
    path("v1/user/status/", UserStatusView.as_view(), name="user_status"),
    path("v1/subscribe/", CreateCheckoutSessionView.as_view(), name="create_checkout_session"),
    path("webhooks/stripe/", stripe_webhook, name="stripe_webhook"),
]
