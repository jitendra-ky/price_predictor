from django.urls import path
from .views import PredictView, PredictionListView

urlpatterns = [
    path("v1/predict/", PredictView.as_view(), name="predict"),
    path("v1/predictions/", PredictionListView.as_view(), name="predictions"),
]
