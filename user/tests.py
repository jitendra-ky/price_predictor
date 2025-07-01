from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User

# Create your tests here.

class RegisterViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('user')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }

    def test_register(self):
        response = self.client.post(self.url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_get_user_unauthenticated(self):
        """Test that unauthenticated users cannot retrieve user data"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_user_authenticated(self):
        """Test that authenticated users can retrieve their own data"""
        user = User.objects.create_user(
            username='authuser', 
            email='auth@example.com', 
            password='authpass123'
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'authuser')
        self.assertEqual(response.data['email'], 'auth@example.com')
        self.assertNotIn('password', response.data)
    
    def test_register_invalid_data(self):
        """Test registration with invalid data"""
        invalid_data = {
            'username': '',
            'email': 'invalid-email',
            'password': ''
        }
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_duplicate_username(self):
        """Test registration with duplicate username"""
        User.objects.create_user(
            username='testuser',
            email='existing@example.com',
            password='existpass123'
        )
        response = self.client.post(self.url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class TokenObtainPairViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('token_obtain_pair')
        self.user = User.objects.create_user(
            username='existinguser', 
            email='exist@example.com', 
            password='existpass123'
        )

    def test_token_obtain_valid_credentials(self):
        """Test token obtain with valid credentials"""
        response = self.client.post(self.url, {
            'username': 'existinguser',
            'password': 'existpass123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_token_obtain_invalid_credentials(self):
        """Test token obtain with invalid credentials"""
        response = self.client.post(self.url, {
            'username': 'existinguser',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_obtain_missing_credentials(self):
        """Test token obtain with missing credentials"""
        response = self.client.post(self.url, {
            'username': 'existinguser'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenRefreshViewTest(APITestCase):
    def setUp(self):
        self.token_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')
        self.user = User.objects.create_user(
            username='refreshuser',
            email='refresh@example.com',
            password='refreshpass123'
        )
    
    def test_token_refresh_valid(self):
        """Test token refresh with valid refresh token"""
        # First, get a token pair
        token_response = self.client.post(self.token_url, {
            'username': 'refreshuser',
            'password': 'refreshpass123'
        }, format='json')
        refresh_token = token_response.data['refresh']
        
        # Now test refresh
        response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_token_refresh_invalid(self):
        """Test token refresh with invalid refresh token"""
        response = self.client.post(self.refresh_url, {
            'refresh': 'invalid_token'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
