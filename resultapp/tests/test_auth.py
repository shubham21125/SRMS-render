import time
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache

class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teststudent', password='password123', email='student@example.com')
        # Ensure rate limit cache is cleared between tests
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_login_page_happy_path(self):
        # GET request renders login form
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

        # POST with invalid credentials returns error
        response = self.client.post(reverse('login'), {'username': 'teststudent', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')

    def test_login_rate_limiting(self):
        # First 5 POST attempts should return invalid credentials (status 200)
        for i in range(5):
            response = self.client.post(reverse('login'), {'username': 'teststudent', 'password': 'wrongpassword'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Invalid username or password.')

        # 6th attempt should trigger rate limiting and return lockout message
        response = self.client.post(reverse('login'), {'username': 'teststudent', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed login attempts. Please try again after 10 minutes.')

    def test_forgot_password_rate_limiting(self):
        # First 5 POST attempts
        for i in range(5):
            response = self.client.post(reverse('admin_forgot_password'), {'email': 'admin@example.com'})
            self.assertEqual(response.status_code, 200) # Re-renders page as no admin user matches

        # 6th attempt should trigger rate limit
        response = self.client.post(reverse('admin_forgot_password'), {'email': 'admin@example.com'})
        self.assertEqual(response.status_code, 200)
        # Lockout message is returned via messages framework, let's verify context/messages
        messages = [m.message for m in response.context['messages']]
        self.assertIn("Too many password reset requests. Please try again after 10 minutes.", messages)

    def test_verify_otp_rate_limiting(self):
        # Set session variable to allow access to verify otp view
        session = self.client.session
        session['reset_email'] = 'admin@example.com'
        session['reset_otp'] = '123456'
        session['reset_otp_expiry'] = time.time() + 600
        session.save()

        # First 5 attempts
        for i in range(5):
            response = self.client.post(reverse('admin_verify_otp'), {'otp': '111111'})
            self.assertEqual(response.status_code, 200)

        # 6th attempt
        response = self.client.post(reverse('admin_verify_otp'), {'otp': '111111'})
        self.assertEqual(response.status_code, 200)
        messages = [m.message for m in response.context['messages']]
        self.assertIn("Too many OTP verification attempts. Please try again after 10 minutes.", messages)
