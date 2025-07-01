from django.test import TestCase, Client
from django.http import JsonResponse
import json

from .views import HealthCheckView


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
