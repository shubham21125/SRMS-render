import io
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from resultapp.models import Student, Class, Subject, Result

class ImportExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin_user', password='password123', email='admin@example.com')
        self.cls = Class.objects.create(class_name='Class 10', class_numeric=10, section='A')
        self.subj = Subject.objects.create(subject_name='Math', subject_code='MATH101', credits=4)
        self.student = Student.objects.create(
            roll_id='S9001', name='John Doe', email='john@example.com',
            student_class=self.cls, dob='2005-01-01', status=1
        )

    def test_export_students_csv_happy_path(self):
        self.client.login(username='admin_user', password='password123')
        
        response = self.client.get(reverse('export_students_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="srms_students.csv"')
        
        content = response.getvalue().decode('utf-8')
        self.assertIn('John Doe', content)
        self.assertIn('S9001', content)

    def test_export_results_csv_happy_path(self):
        # Create some results first
        Result.objects.create(
            student=self.student, student_class=self.cls, subject=self.subj, semester=1,
            theory_marks=28, internal_marks=19
        )
        
        self.client.login(username='admin_user', password='password123')
        
        response = self.client.get(reverse('export_results_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="srms_results.csv"')
        
        content = response.getvalue().decode('utf-8')
        self.assertIn('S9001', content)
        self.assertIn('MATH101', content)

    def test_import_results_csv_happy_path(self):
        self.client.login(username='admin_user', password='password123')
        
        csv_content = (
            "Roll ID,Subject Code,Theory (30),Internal (20),Practical (25),Oral (25)\n"
            "S9001,MATH101,25,18,22,23\n"
        )
        csv_file = SimpleUploadedFile("results.csv", csv_content.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('import_results_csv'), {'csv_file': csv_file})
        self.assertEqual(response.status_code, 302) # Redirects back to import_export view
        
        # Verify results imported
        self.assertEqual(Result.objects.filter(student=self.student).count(), 1)
        r = Result.objects.get(student=self.student, subject=self.subj)
        self.assertEqual(r.theory_marks, 25)
        self.assertEqual(r.internal_marks, 18)
        self.assertEqual(r.practical_marks, 22)
        self.assertEqual(r.oral_marks, 23)

    def test_import_results_csv_validation_failure(self):
        self.client.login(username='admin_user', password='password123')
        
        # Invalid roll ID and out of range theory marks
        csv_content = (
            "Roll ID,Subject Code,Theory (30),Internal (20),Practical (25),Oral (25)\n"
            "INVALID_ROLL,MATH101,45,18,22,23\n"
        )
        csv_file = SimpleUploadedFile("results.csv", csv_content.encode('utf-8'), content_type="text/csv")
        
        response = self.client.post(reverse('import_results_csv'), {'csv_file': csv_file})
        self.assertEqual(response.status_code, 302)
        
        # Verify no results created
        self.assertEqual(Result.objects.count(), 0)
