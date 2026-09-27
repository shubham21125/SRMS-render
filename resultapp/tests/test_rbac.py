from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from resultapp.models import Teacher, Parent, Student, Class

class RbacTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users
        self.admin_user = User.objects.create_superuser(username='admin_user', password='password123', email='admin@example.com')
        
        self.teacher_user = User.objects.create_user(username='teacher_user', password='password123', email='teacher@example.com')
        self.teacher = Teacher.objects.create(user=self.teacher_user, department='CS')

        self.parent_user = User.objects.create_user(username='parent_user', password='password123', email='parent@example.com')
        self.cls = Class.objects.create(class_name='Class 10', class_numeric=10, section='A')
        self.student = Student.objects.create(roll_id='S100', name='Test Student', email='teststudent@example.com', student_class=self.cls, status=1)
        self.parent = Parent.objects.create(user=self.parent_user, student=self.student, relationship='father')

        self.student_user = User.objects.create_user(username='student_user', password='password123', email='teststudent@example.com')
        # Link student user
        self.student.user = self.student_user
        self.student.save()

    def test_unauthenticated_redirects(self):
        urls = [
            'admin_dashboard',
            'teacher_dashboard',
            'parent_dashboard',
            'create_branch',
            'manage_branches',
            'add_student',
            'manage_students',
            'import_export',
        ]
        for url in urls:
            response = self.client.get(reverse(url))
            self.assertEqual(response.status_code, 302, f"URL {url} should redirect when unauthenticated")

    def test_admin_access_boundaries(self):
        self.client.login(username='admin_user', password='password123')
        
        # Admin can access admin pages
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('create_branch'))
        self.assertEqual(response.status_code, 200)

        # Admin cannot access teacher dashboard (redirects)
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Admin cannot access parent dashboard (redirects)
        response = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_teacher_access_boundaries(self):
        self.client.login(username='teacher_user', password='password123')

        # Teacher can access teacher dashboard
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Teacher cannot access admin page (redirects to login)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Teacher cannot access parent page
        response = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_parent_access_boundaries(self):
        self.client.login(username='parent_user', password='password123')

        # Parent can access parent dashboard
        response = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Parent cannot access admin dashboard
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Parent cannot access teacher dashboard
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 302)
