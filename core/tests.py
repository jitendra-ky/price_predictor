from django.test import TestCase, Client
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import timedelta
import json

from .views import HealthCheckView
from .models import Prediction
from .tasks import run_stock_prediction

User = get_user_model()


class HealthCheckViewTest(TestCase):
    """Test cases for HealthCheckView"""
    
    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.view = HealthCheckView()
    
    def test_health_check_get_request(self):
        """Test GET request to health check endpoint returns correct response"""
        # Create a mock request
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/health/')
        
        # Call the view directly
        response = self.view.get(request)
        
        # Assertions
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON content
        response_data = json.loads(response.content)
        self.assertEqual(response_data, {"status": "ok"})


class PredictViewTest(APITestCase):
    """Test cases for PredictView"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
    def test_predict_missing_ticker(self):
        """Test POST request without ticker returns 400"""
        url = reverse('predict')
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Ticker is required')
    
    def test_predict_unauthenticated(self):
        """Test POST request without authentication returns 401"""
        self.client.force_authenticate(user=None)
        url = reverse('predict')
        response = self.client.post(url, {'ticker': 'AAPL'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('core.views.StockPredictor')
    def test_predict_success(self, mock_predictor_class):
        """Test successful prediction creates prediction and returns data"""
        # Mock the predictor
        mock_predictor = MagicMock()
        mock_predictor.run.return_value = {
            'ticker': 'AAPL',
            'next_day_price': 150.25,
            'mse': 2.5,
            'rmse': 1.58,
            'r2': 0.85,
            'plot_urls': ['plot1.png', 'plot2.png']
        }
        mock_predictor_class.return_value = mock_predictor
        
        url = reverse('predict')
        response = self.client.post(url, {'ticker': 'AAPL'})
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ticker'], 'AAPL')
        
        # Verify prediction was created in database
        self.assertEqual(Prediction.objects.count(), 1)
        prediction = Prediction.objects.first()
        self.assertEqual(prediction.user, self.user)
        self.assertEqual(prediction.ticker, 'AAPL')
    
    @patch('core.views.StockPredictor')
    def test_predict_predictor_exception(self, mock_predictor_class):
        """Test predictor exception returns 500"""
        mock_predictor_class.side_effect = Exception('Prediction failed')
        
        url = reverse('predict')
        response = self.client.post(url, {'ticker': 'INVALID'})
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'Prediction failed')


class PredictionListViewTest(APITestCase):
    """Test cases for PredictionListView"""
    
    def setUp(self):
        """Set up test client, users and predictions"""
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Create predictions for user1 with explicit timestamps
        now = timezone.now()
        self.prediction1 = Prediction.objects.create(
            user=self.user1,
            ticker='AAPL',
            metrics={'next_day_price': 150.0, 'mse': 2.0, 'rmse': 1.4, 'r2': 0.8},
            plot_urls=['plot1.png']
        )
        # Manually set created time to ensure proper ordering
        self.prediction1.created = now - timedelta(minutes=10)
        self.prediction1.save()
        
        self.prediction2 = Prediction.objects.create(
            user=self.user1,
            ticker='GOOGL',
            metrics={'next_day_price': 2500.0, 'mse': 10.0, 'rmse': 3.2, 'r2': 0.9},
            plot_urls=['plot2.png']
        )
        # This one should be newer (created later)
        self.prediction2.created = now
        self.prediction2.save()
        
        # Create prediction for user2
        self.prediction3 = Prediction.objects.create(
            user=self.user2,
            ticker='TSLA',
            metrics={'next_day_price': 800.0, 'mse': 5.0, 'rmse': 2.2, 'r2': 0.75},
            plot_urls=['plot3.png']
        )
    
    def test_prediction_list_unauthenticated(self):
        """Test GET request without authentication returns 401"""
        url = reverse('predictions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_prediction_list_success(self):
        """Test authenticated user gets their predictions only"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('predictions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that only user1's predictions are returned
        tickers = [pred['ticker'] for pred in response.data]
        self.assertIn('AAPL', tickers)
        self.assertIn('GOOGL', tickers)
        self.assertNotIn('TSLA', tickers)
    
    def test_prediction_list_ordered_by_created(self):
        """Test predictions are ordered by created date (newest first)"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('predictions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The second prediction (GOOGL) should be first as it was created later
        self.assertEqual(response.data[0]['ticker'], 'GOOGL')
        self.assertEqual(response.data[1]['ticker'], 'AAPL')
    
    def test_prediction_list_empty_for_new_user(self):
        """Test new user with no predictions gets empty list"""
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=new_user)
        url = reverse('predictions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class CeleryTaskTest(APITestCase):
    """Test cases for Celery tasks"""
    
    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username='taskuser',
            email='task@example.com',
            password='testpass123'
        )
    
    @patch('core.tasks.StockPredictor')
    def test_run_stock_prediction_success(self, mock_predictor_class):
        """Test successful execution of run_stock_prediction task"""
        # Mock the predictor
        mock_predictor = MagicMock()
        mock_predictor.run.return_value = {
            'ticker': 'AAPL',
            'next_day_price': 150.25,
            'mse': 2.5,
            'rmse': 1.58,
            'r2': 0.85,
            'plot_urls': ['plot1.png', 'plot2.png']
        }
        mock_predictor_class.return_value = mock_predictor
        
        # Execute the task
        result = run_stock_prediction(self.user.id, 'AAPL')
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['ticker'], 'AAPL')
        self.assertEqual(result['next_day_price'], 150.25)
        self.assertIn('prediction_id', result)
        
        # Verify prediction was saved to database
        prediction = Prediction.objects.get(id=result['prediction_id'])
        self.assertEqual(prediction.user, self.user)
        self.assertEqual(prediction.ticker, 'AAPL')
        self.assertEqual(prediction.metrics['next_day_price'], 150.25)
        self.assertEqual(prediction.plot_urls, ['plot1.png', 'plot2.png'])
    
    def test_run_stock_prediction_invalid_user(self):
        """Test task with non-existent user ID"""
        result = run_stock_prediction(99999, 'AAPL')
        
        self.assertFalse(result['success'])
        self.assertIn('User with id 99999 does not exist', result['error'])
    
    @patch('core.tasks.StockPredictor')
    def test_run_stock_prediction_predictor_error(self, mock_predictor_class):
        """Test task when StockPredictor raises an exception"""
        mock_predictor_class.side_effect = ValueError('Invalid ticker symbol')
        
        result = run_stock_prediction(self.user.id, 'INVALID')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid ticker symbol')
        
        # Verify no prediction was created
        self.assertEqual(Prediction.objects.count(), 0)
