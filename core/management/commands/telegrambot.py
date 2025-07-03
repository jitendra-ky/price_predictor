"""
Django management command for running the Telegram bot
"""
import logging

from django.core.management.base import BaseCommand
from core.telegram.bot import create_application
from telegram import Update

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts the Telegram bot'

    def handle(self, *args, **options):
        """
        Runs the Telegram bot in polling mode
        """
        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))
        
        # Create the Application and run it
        try:
            application = create_application()
            self.stdout.write(self.style.SUCCESS('Bot is running...'))
            
            # Run the bot until the user presses Ctrl-C
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))
