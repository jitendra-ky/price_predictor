from django.views import View
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
import pytz
from .models import Prediction
from .serializers import PredictionSerializer
from .services.predictor import StockPredictor
from .utils import check_rate_limit

class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"}, status=200)


class PredictView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check rate limit
        is_allowed, remaining, reset_time = check_rate_limit(f"user:{request.user.id}", window_minutes=1)
        
        if not is_allowed:
            ist_tz = pytz.timezone('Asia/Kolkata')
            reset_time_ist = reset_time.astimezone(ist_tz) if reset_time else None
            reset_time_str = reset_time_ist.strftime("%Y-%m-%d %H:%M:%S IST") if reset_time_ist else "Unknown"
            return Response({
                "error": f"Rate limit exceeded. You can only make {settings.PREDICT_PER_MIN} predictions per minute. Try again after {reset_time_str}",
                "remaining_requests": remaining,
                "reset_time": reset_time_str
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        ticker = request.data.get("ticker")
        if not ticker:
            return Response({"error": "Ticker is required"}, status=status.HTTP_400_BAD_REQUEST)
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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PredictionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        prediction = Prediction.objects.filter(user=request.user).order_by('-created')
        serializer = PredictionSerializer(prediction, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)