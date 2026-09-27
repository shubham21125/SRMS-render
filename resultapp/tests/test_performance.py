from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from resultapp.models import Student, Class, Subject, Result

class PerformanceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin_perf', password='password123', email='admin@example.com')
        self.cls = Class.objects.create(class_name='Class 10', class_numeric=10, section='A')
        self.subj = Subject.objects.create(subject_name='Math', subject_code='MATH101', credits=4)
        self.student = Student.objects.create(
            roll_id='S5001', name='John Doe', email='john@example.com',
            student_class=self.cls, dob='2005-01-01', status=1
        )
        self.res = Result.objects.create(
            student=self.student, student_class=self.cls, subject=self.subj, semester=1,
            theory_marks=28, internal_marks=19
        )
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_analytics_caching_and_invalidation(self):
        self.client.login(username='admin_perf', password='password123')
        
        # Verify cache is initially empty
        cache_key = 'admin_analytics_data'
        self.assertIsNone(cache.get(cache_key))

        # First request (Cache Miss)
        response = self.client.get(reverse('admin_analytics'))
        self.assertEqual(response.status_code, 200)

        # Cache should now be populated
        cached_val = cache.get(cache_key)
        self.assertIsNotNone(cached_val)
        self.assertEqual(cached_val['total_students'], 1)
        self.assertEqual(cached_val['passed_count'], 1)

        # Modify result to trigger post_save signal and invalidate cache
        self.res.theory_marks = 10  # This makes it a fail, but the key is invalidation
        self.res.save()

        # Cache should be cleared/invalidated (None)
        self.assertIsNone(cache.get(cache_key))
