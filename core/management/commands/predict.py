from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from core.models import Prediction
from core.services.predictor import StockPredictor

User = get_user_model()


class Command(BaseCommand):
    help = 'Run stock price predictions for specific ticker or all predefined tickers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker',
            type=str,
            help='Stock ticker symbol to predict (e.g., TSLA, AAPL)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run predictions for all predefined tickers',
        )

    def handle(self, *args, **options):
        # Predefined list of tickers for --all option
        predefined_tickers = ['TSLA', 'AAPL', 'MSFT']
        
        ticker = options.get('ticker')
        run_all = options.get('all')
        
        # Validate arguments
        if not ticker and not run_all:
            raise CommandError('You must specify either --ticker TICKER or --all')
        
        if ticker and run_all:
            raise CommandError('You cannot use both --ticker and --all options together')
        
        # Get or create a system user for management command predictions
        system_user, created = User.objects.get_or_create(
            username='system_predictor',
            defaults={
                'email': 'system@prediction.com',
                'first_name': 'System',
                'last_name': 'Predictor'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created system user for predictions')
            )
        
        # Determine which tickers to process
        tickers_to_process = [ticker] if ticker else predefined_tickers
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting predictions for: {", ".join(tickers_to_process)}')
        )
        
        for ticker_symbol in tickers_to_process:
            self.run_prediction(ticker_symbol, system_user)
    
    def run_prediction(self, ticker, user):
        """Run prediction for a single ticker and save to database"""
        try:
            self.stdout.write(f'\nProcessing {ticker}...')
            
            # Create predictor instance and run prediction
            predictor = StockPredictor(ticker)
            result = predictor.run()
            
            # Save prediction to database
            prediction = Prediction.objects.create(
                user=user,
                ticker=result['ticker'],
                metrics={
                    'next_day_price': result['next_day_price'],
                    'mse': result['mse'],
                    'rmse': result['rmse'],
                    'r2': result['r2']
                },
                plot_urls=result['plot_urls']
            )
            
            # Print results to console
            self.stdout.write(
                self.style.SUCCESS(f'✓ Prediction completed for {ticker}')
            )
            self.stdout.write(f'  Ticker: {result["ticker"]}')
            self.stdout.write(f'  Predicted next-day price: ${result["next_day_price"]}')
            self.stdout.write(f'  MSE: {result["mse"]}')
            self.stdout.write(f'  RMSE: {result["rmse"]}')
            self.stdout.write(f'  R²: {result["r2"]}')
            self.stdout.write(f'  Plot URLs: {", ".join(result["plot_urls"])}')
            self.stdout.write(f'  Saved to database with ID: {prediction.id}')
            
        except ValueError as e:
            # Handle invalid ticker or data fetch errors
            self.stdout.write(
                self.style.ERROR(f'✗ Error processing {ticker}: {str(e)}')
            )
        except FileNotFoundError as e:
            # Handle model file not found
            self.stdout.write(
                self.style.ERROR(f'✗ Model file error for {ticker}: {str(e)}')
            )
        except Exception as e:
            # Handle any other unexpected errors
            self.stdout.write(
                self.style.ERROR(f'✗ Unexpected error processing {ticker}: {str(e)}')
            )
