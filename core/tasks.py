import os
import asyncio

from celery import shared_task
from django.contrib.auth import get_user_model
from django.conf import settings
import logging
import traceback
from telegram import Bot
from telegram.error import TelegramError
from .models import Prediction
from .services.predictor import StockPredictor

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

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


@shared_task
def run_stock_prediction_telegram(user_id, ticker, chat_id):
    """
    Celery task to run stock prediction and send results back to Telegram.
    
    Args:
        user_id (int): The ID of the user requesting the prediction
        ticker (str): The stock ticker symbol to predict
        chat_id (str): The Telegram chat ID to send results to
        
    Returns:
        dict: Status of the operation
    """
    try:
        logger.info(f"Running stock prediction for ticker {ticker}, user {user_id}, chat {chat_id}")
        
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
        
        # Send results back to the user via Telegram
        asyncio.run(send_telegram_prediction_result(chat_id, result))
        
        return {
            "success": True,
            "prediction_id": prediction.id,
            "ticker": result['ticker'],
            "chat_id": chat_id
        }
        
    except User.DoesNotExist:
        error_msg = f"User with id {user_id} does not exist"
        logger.error(error_msg)
        asyncio.run(send_telegram_error(chat_id, error_msg))
        return {"success": False, "error": error_msg}
        
    except Exception as e:
        error_msg = f"Error predicting {ticker}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        asyncio.run(send_telegram_error(chat_id, error_msg))
        return {"success": False, "error": error_msg}


async def send_telegram_prediction_result(chat_id, prediction_result):
    """
    Send the prediction result to a Telegram chat.
    
    Args:
        chat_id (str): The Telegram chat ID to send the message to
        prediction_result (dict): The prediction result dictionary from StockPredictor
    """
    try:
        # Create bot instance
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        # Format the prediction message
        ticker = prediction_result['ticker']
        next_day_price = prediction_result['next_day_price']
        mse = prediction_result['mse']
        rmse = prediction_result['rmse']
        r2 = prediction_result['r2']
        
        message = (
            f"📊 *Stock Prediction: {ticker}*\n\n"
            f"*Next Day Price:* ${next_day_price}\n\n"
            f"*Metrics:*\n"
            f"- MSE: {mse}\n"
            f"- RMSE: {rmse}\n"
            f"- R²: {r2}\n"
        )
        
        # Send the text message
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        
        # Send the plot images
        base_url = settings.BASE_URL if hasattr(settings, 'BASE_URL') else ''
        
        for plot_url in prediction_result['plot_urls']:
            full_url = f"{base_url}{plot_url}"
            try:
                # Try to send the image directly from the file path
                image_path = os.path.join(settings.MEDIA_ROOT, plot_url.lstrip('/media/'))
                
                if os.path.exists(image_path):
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=open(image_path, 'rb'),
                        caption=f"{ticker} - {os.path.basename(plot_url)}"
                    )
                else:
                    # If the file doesn't exist locally, send the URL
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"Plot available at: {full_url}"
                    )
            except Exception as e:
                logger.error(f"Error sending plot image: {e}")
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"Plot available at: {full_url}"
                )
                
        logger.info(f"Sent prediction results to chat_id {chat_id}")
        
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
    except Exception as e:
        logger.error(f"Error sending prediction results: {e}")


async def send_telegram_error(chat_id, error_message):
    """
    Send an error message to a Telegram chat.
    
    Args:
        chat_id (str): The Telegram chat ID to send the message to
        error_message (str): The error message to send
    """
    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        message = (
            f"❌ *Error*\n\n"
            f"{error_message}\n\n"
            f"Please try again later or contact support."
        )
        
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        
        logger.info(f"Sent error message to chat_id {chat_id}")
        
    except Exception as e:
        logger.error(f"Error sending error message to Telegram: {e}")