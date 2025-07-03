"""
Telegram Bot implementation for Stock Price Prediction service
"""
import logging
import random
import string
from typing import Dict, Any

from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from core.models import TelegramProfile

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
        "Available commands:\n\n"
        "/start - Start the bot and register your chat\n"
        "/predict <ticker> - Get price prediction for a stock ticker\n"
        "/latest - Get your latest predictions\n"
        "/help - Show this help message"
    )
    
    await update.message.reply_text(help_text)


def create_application() -> Application:
    """
    Create and configure the Telegram bot application.
    """
    from django.conf import settings
    
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
    
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Error handler for the Telegram bot.
    """
    logger.error(f"Exception while handling an update: {context.error}")
