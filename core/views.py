from django.views import View
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Prediction
from .serializers import PredictionSerializer
from .services.predictor import StockPredictor
from .tasks import run_stock_prediction

class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"}, status=200)


class PredictView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        ticker = request.data.get("ticker")
        if not ticker:
            return Response({"error": "Ticker is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Queue the prediction task
        task = run_stock_prediction.delay(request.user.id, ticker)
        
        return Response({
            "message": "Prediction started. Please check back soon.",
            "task_id": task.id,
            "ticker": ticker
        }, status=status.HTTP_202_ACCEPTED)

class PredictionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        prediction = Prediction.objects.filter(user=request.user).order_by('-created')
        serializer = PredictionSerializer(prediction, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)