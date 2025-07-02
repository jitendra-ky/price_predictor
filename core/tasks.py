from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Prediction
from .services.predictor import StockPredictor

User = get_user_model()

@shared_task
def run_stock_prediction(user_id, ticker):
    """
    Celery task to run stock prediction in the background.
    
    Args:
        user_id (int): The ID of the user requesting the prediction
        ticker (str): The stock ticker symbol to predict
    
    Returns:
        dict: The prediction result with metrics and plot URLs
    """
    try:
        # Get the user
        user = User.objects.get(id=user_id)
        
        # Run the prediction
        predictor = StockPredictor(ticker)
        result = predictor.run()
        
        # Save the prediction to the database
        prediction = Prediction.objects.create(
            user=user,
            ticker=result['ticker'],
            metrics={
                "next_day_price": result["next_day_price"],
                "mse": result["mse"],
                "rmse": result["rmse"],
                "r2": result["r2"],
            },
            plot_urls=result["plot_urls"]
        )
        
        return {
            "success": True,
            "prediction_id": prediction.id,
            "ticker": result['ticker'],
            "next_day_price": result["next_day_price"]
        }
        
    except User.DoesNotExist:
        return {
            "success": False,
            "error": f"User with id {user_id} does not exist"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }