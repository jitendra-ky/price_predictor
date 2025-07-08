"""
Telegram Bot implementation for Stock Price Prediction service
"""
import logging
import random
import string
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from core.models import TelegramProfile
from core.tasks import run_stock_prediction_telegram

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

User = get_user_model()


# Synchronous database operations wrapped for async usage
@sync_to_async
def check_user_exists(username):
    return User.objects.filter(username=username).exists()


@sync_to_async
def get_first_user():
    return User.objects.first()


@sync_to_async
def get_latest_prediction(user):
    """
    Get the latest prediction for a user, ordered by creation date descending.
    """
    return user.predictions.order_by('-created').first()


@sync_to_async
def create_telegram_user(chat_id, first_name, last_name=None):
    """
    Create a user with tg_<chat_id> username format
    """
    username = f"tg_{chat_id}"
    # Generate a random password
    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # Create user with Telegram information
    user = User.objects.create_user(
        username=username,
        email=f"{username}@telegram-temp.example.com",  # Placeholder email
        password=random_password,
        first_name=first_name or "",
        last_name=last_name or ""
    )
    
    return user


@sync_to_async
def update_or_create_telegram_profile(chat_id, user):
    return TelegramProfile.objects.update_or_create(
        chat_id=str(chat_id),
        defaults={"user": user}
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /start command.
    Greets the user and saves their chat_id.
    """
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    
    logger.info(f"Start command received from {username} (chat_id: {chat_id})")
    
    welcome_message = (
        f"Hello {first_name}! Welcome to the Stock Price Prediction bot.\n\n"
        f"Use /help to see available commands."
    )
    
    await update.message.reply_text(welcome_message)
    
    # Store the chat_id in the database
    try:
        # Check if a user with this telegram username pattern already exists
        telegram_username = f"tg_{chat_id}"
        user_exists = await check_user_exists(telegram_username)
        
        if not user_exists:
            # Create a new user with the telegram chat_id as username prefix
            user = await create_telegram_user(chat_id, first_name, last_name)
            logger.info(f"Created new Django user with username {telegram_username}")
        else:
            # Get the existing telegram user
            user = await sync_to_async(User.objects.get)(username=telegram_username)
            logger.info(f"Using existing Django user with username {telegram_username}")
        
        # Store or update the chat_id
        telegram_profile, created = await update_or_create_telegram_profile(chat_id, user)
        
        if created:
            logger.info(f"Created new TelegramProfile for chat_id {chat_id}")
        else:
            logger.info(f"Updated existing TelegramProfile for chat_id {chat_id}")
            
    except Exception as e:
        logger.error(f"Error saving chat_id: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /help command.
    Shows available bot commands.
    """
    help_text = (
        "🤖 *Stock Prediction Bot Commands*\n\n"
        "/start - Register and get started\n"
        "/help - Show this help message\n"
        "/predict <ticker> - Get price prediction for a stock ticker\n"
        "/latest - Get your latest prediction\n"
        "/subscribe - Upgrade to Pro (unlimited predictions)\n"
        "/stats - View your statistics (Pro only)\n\n"
        "Example: /predict TSLA"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /predict command.
    Format: /predict <ticker>
    
    This handler validates the ticker argument and queues a Celery task
    to run the prediction asynchronously.
    """
    # Get the chat_id from the update
    chat_id = update.effective_chat.id
    
    # Check if ticker was provided
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Please provide a ticker symbol. Example: /predict TSLA"
        )
        return
    
    # Get the ticker symbol from arguments
    ticker = context.args[0].upper()
    
    logger.info(f"Prediction requested for ticker {ticker} by chat_id {chat_id}")
    
    try:
        # Get the user from the TelegramProfile
        logger.info(f"Fetching TelegramProfile for chat_id {chat_id}")
        telegram_profile = await sync_to_async(lambda: TelegramProfile.objects.select_related("user").get(chat_id=str(chat_id)))()
        user = telegram_profile.user
        logger.info(f"Found user {user.username} for chat_id {chat_id}")
        
        # Check quota before processing
        profile = await sync_to_async(lambda: getattr(user, 'userprofile', None))()
        if profile and not await sync_to_async(profile.can_make_prediction)():
            remaining = await sync_to_async(profile.get_remaining_predictions)()
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            
            await update.message.reply_text(
                f"🚫 *Daily limit reached!*\n\n"
                f"You've used all 5 free predictions today.\n"
                f"Remaining: {remaining}\n\n"
                f"💎 Upgrade to Pro for unlimited predictions!\n"
                f"🔗 [Subscribe here]({base_url}/api/v1/subscribe)\n\n"
                f"Pro features:\n"
                f"• Unlimited /predict calls\n"
                f"• /stats command access\n"
                f"• Priority processing",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            return
        
        # Increment usage count if profile exists
        if profile:
            await sync_to_async(profile.increment_prediction_count)()
        
        # Send immediate response
        await update.message.reply_text(f"Prediction started for {ticker}...")
        
        logger.info(f"Queuing prediction task for user {user.username} with ticker {ticker}")
        # Queue the Celery task
        await sync_to_async(run_stock_prediction_telegram.delay)(
            user.id, 
            ticker, 
            chat_id
        )
        logger.info(f"Prediction task queued for user {user.username} with ticker {ticker}")
        
    except TelegramProfile.DoesNotExist:
        await update.message.reply_text(
            "Your Telegram profile isn't linked yet. Please use /start to register."
        )
    except Exception as e:
        logger.error(f"Error queuing prediction task: {e}")
        await update.message.reply_text(
            f"Sorry, an error occurred: {str(e)}"
        )


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /latest command.
    Retrieves and displays the user's most recent prediction.
    """
    chat_id = update.effective_chat.id
    
    logger.info(f"Latest prediction requested by chat_id {chat_id}")
    
    try:
        # Get the user from the TelegramProfile
        telegram_profile = await sync_to_async(lambda: TelegramProfile.objects.select_related("user").get(chat_id=str(chat_id)))()
        user = telegram_profile.user
        
        # Get the latest prediction for this user
        latest_prediction = await get_latest_prediction(user)
        
        if not latest_prediction:
            await update.message.reply_text("You have no predictions yet.")
            return
        
        # Format the prediction message
        ticker = latest_prediction.ticker
        created_date = latest_prediction.created.strftime("%Y-%m-%d %H:%M UTC")
        metrics = latest_prediction.metrics
        plot_urls = latest_prediction.plot_urls
        
        next_day_price = metrics.get('next_day_price', 'N/A')
        mse = metrics.get('mse', 'N/A')
        rmse = metrics.get('rmse', 'N/A')
        r2 = metrics.get('r2', 'N/A')
        
        message = (
            f"📊 *Latest Prediction: {ticker}*\n\n"
            f"*Created:* {created_date}\n"
            f"*Next Day Price:* ${next_day_price}\n\n"
            f"*Metrics:*\n"
            f"- MSE: {mse}\n"
            f"- RMSE: {rmse}\n"
            f"- R²: {r2}\n"
        )
        
        # Send the text message
        await update.message.reply_text(message, parse_mode="Markdown")
        
        # Send the plot images if they exist
        if plot_urls:
            base_url = getattr(settings, 'BASE_URL', '')
            
            for plot_url in plot_urls:
                try:
                    # Try to send the image directly from the file path
                    image_path = os.path.join(settings.MEDIA_ROOT, plot_url.lstrip('/media/'))
                    
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as photo_file:
                            await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo_file,
                                caption=f"{ticker} - {os.path.basename(plot_url)}"
                            )
                    else:
                        # If the file doesn't exist locally, send the URL
                        full_url = f"{base_url}{plot_url}"
                        await update.message.reply_text(f"Plot available at: {full_url}")
                        
                except Exception as e:
                    logger.error(f"Error sending plot image for latest prediction: {e}")
                    # Send URL as fallback
                    full_url = f"{base_url}{plot_url}"
                    await update.message.reply_text(f"Plot available at: {full_url}")
        
        logger.info(f"Sent latest prediction for user {user.username} to chat_id {chat_id}")
        
    except TelegramProfile.DoesNotExist:
        await update.message.reply_text(
            "Your Telegram profile isn't linked yet. Please use /start to register."
        )
    except Exception as e:
        logger.error(f"Error retrieving latest prediction: {e}")
        await update.message.reply_text(
            f"Sorry, an error occurred while retrieving your latest prediction: {str(e)}"
        )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /subscribe command.
    Provides a link to upgrade to Pro subscription.
    """
    chat_id = update.effective_chat.id
    
    try:
        # Get the user from the TelegramProfile
        telegram_profile = await sync_to_async(lambda: TelegramProfile.objects.select_related("user").get(chat_id=str(chat_id)))()
        user = telegram_profile.user
        
        # Check if user is already Pro
        profile = await sync_to_async(lambda: getattr(user, 'userprofile', None))()
        if profile and profile.is_pro:
            await update.message.reply_text(
                "🎉 You're already a Pro subscriber!\n\n"
                "Enjoy unlimited predictions and priority support."
            )
            return
        
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        
        await update.message.reply_text(
            "💎 *Upgrade to Pro!*\n\n"
            "Get unlimited predictions for just ₹199/month\n\n"
            "*Pro Features:*\n"
            "• 🚀 Unlimited /predict calls per day\n"
            "• 📊 Access to /stats command\n"
            "• ⚡ Priority processing queue\n"
            "• 🎯 Advanced prediction metrics\n\n"
            f"🔗 [Subscribe Now]({base_url}/api/v1/subscribe)\n\n"
            "Secure payment powered by Stripe 🔒",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
    except TelegramProfile.DoesNotExist:
        await update.message.reply_text(
            "Your Telegram profile isn't linked yet. Please use /start to register."
        )
    except Exception as e:
        logger.error(f"Error in subscribe command: {e}")
        await update.message.reply_text(
            f"Sorry, an error occurred: {str(e)}"
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /stats command.
    Available only to Pro users.
    """
    chat_id = update.effective_chat.id
    
    try:
        # Get the user from the TelegramProfile
        telegram_profile = await sync_to_async(lambda: TelegramProfile.objects.select_related("user").get(chat_id=str(chat_id)))()
        user = telegram_profile.user
        
        # Check if user is Pro
        profile = await sync_to_async(lambda: getattr(user, 'userprofile', None))()
        if not profile or not profile.is_pro:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            await update.message.reply_text(
                "🔒 *Pro Feature Only*\n\n"
                "The /stats command is available only to Pro subscribers.\n\n"
                f"💎 [Upgrade to Pro]({base_url}/api/v1/subscribe) for ₹199/month\n\n"
                "Pro features include:\n"
                "• 📊 Detailed usage statistics\n"
                "• 🚀 Unlimited predictions\n"
                "• ⚡ Priority processing",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            return
        
        # Get user statistics
        total_predictions = await sync_to_async(lambda: user.predictions.count())()
        today_predictions = await sync_to_async(lambda: profile.daily_predictions_count if profile.last_prediction_date == profile.last_prediction_date else 0)()
        
        # Get subscription info
        subscription = await sync_to_async(lambda: user.subscriptions.filter(status__in=['active', 'trialing']).first())()
        
        message = (
            f"📊 *Your Pro Statistics*\n\n"
            f"👤 *User:* {user.username}\n"
            f"💎 *Status:* Pro Subscriber\n\n"
            f"📈 *Predictions:*\n"
            f"• Today: {today_predictions}\n"
            f"• Total: {total_predictions}\n"
            f"• Daily Limit: Unlimited ∞\n\n"
        )
        
        if subscription:
            message += (
                f"💳 *Subscription:*\n"
                f"• Status: {subscription.status.title()}\n"
                f"• Period: {subscription.current_period_start.strftime('%Y-%m-%d')} to {subscription.current_period_end.strftime('%Y-%m-%d')}\n"
            )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except TelegramProfile.DoesNotExist:
        await update.message.reply_text(
            "Your Telegram profile isn't linked yet. Please use /start to register."
        )
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await update.message.reply_text(
            f"Sorry, an error occurred: {str(e)}"
        )


def create_application() -> Application:
    """
    Create and configure the Telegram bot application.
    """
    
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
    
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("predict", predict_command))
    application.add_handler(CommandHandler("latest", latest_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Error handler for the Telegram bot.
    """
    logger.error(f"Exception while handling an update: {context.error}")
