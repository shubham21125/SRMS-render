from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from resultapp.models import Student, Class, Subject, Result, Parent

class ResultTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin_user', password='password123', email='admin@example.com')
        self.cls = Class.objects.create(class_name='Class 10', class_numeric=10, section='A')
        self.subj1 = Subject.objects.create(subject_name='Math', subject_code='MATH101', credits=4)
        self.subj2 = Subject.objects.create(subject_name='Science', subject_code='SCI102', credits=3)

        self.student = Student.objects.create(
            roll_id='S9001', name='John Doe', email='john@example.com',
            student_class=self.cls, dob='2005-01-01', status=1
        )
        self.parent_user = User.objects.create_user(username='parent_user', password='password123', email='parent@example.com')
        self.parent = Parent.objects.create(user=self.parent_user, student=self.student, relationship='father')

    def test_add_result_happy_path(self):
        self.client.login(username='admin_user', password='password123')
        
        post_data = {
            'class': self.cls.id,
            'studentid': self.student.id,
            'semester': '1',
            f'theory_{self.subj1.id}': '25',
            f'internal_{self.subj1.id}': '18',
            f'theory_{self.subj2.id}': '28',
            f'internal_{self.subj2.id}': '19',
        }
        
        response = self.client.post(reverse('add_result'), post_data)
        self.assertEqual(response.status_code, 302) # Redirects to add_result on success
        
        # Verify results created
        results = Result.objects.filter(student=self.student)
        self.assertEqual(results.count(), 2)
        r1 = results.get(subject=self.subj1)
        self.assertEqual(r1.theory_marks, 25)
        self.assertEqual(r1.internal_marks, 18)

    def test_add_result_invalid_marks(self):
        self.client.login(username='admin_user', password='password123')
        
        # Post non-integer values
        post_data = {
            'class': self.cls.id,
            'studentid': self.student.id,
            'semester': '1',
            f'theory_{self.subj1.id}': 'abc',
            f'internal_{self.subj1.id}': '18',
        }
        
        response = self.client.post(reverse('add_result'), post_data)
        self.assertEqual(response.status_code, 302)
        # Verify no result was created
        self.assertEqual(Result.objects.filter(student=self.student).count(), 0)

    def test_pdf_download_happy_path(self):
        # Create some results first
        Result.objects.create(
            student=self.student, student_class=self.cls, subject=self.subj1, semester=1,
            theory_marks=28, internal_marks=19
        )
        
        self.client.login(username='parent_user', password='password123')
        
        # Request PDF download
        response = self.client.get(reverse('parent_download_result_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename="Result_Card_S9001.pdf"'))
        self.assertGreater(len(response.content), 0)
