from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from resultapp.models import (
    Student, Class, Subject, Result, Parent, Teacher, AuditLog, WhatsAppLog,
    Branch, BranchSubject, SubjectCombination, Attendance
)
from resultapp.whatsapp import send_whatsapp_message

class Block3FeaturesTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Setup class, subject
        self.cls1 = Class.objects.create(class_name='Class A', class_numeric=10, section='A')
        self.cls2 = Class.objects.create(class_name='Class B', class_numeric=10, section='B')
        self.subj = Subject.objects.create(subject_name='Math', subject_code='MATH101', credits=4)

        # Setup users
        self.admin_user = User.objects.create_superuser(username='admin_u', password='password123', email='admin@example.com')
        
        self.student_user = User.objects.create_user(username='student_u', password='password123', email='student@example.com')
        self.student = Student.objects.create(roll_id='S11', name='Student One', email='student@example.com', student_class=self.cls1, status=1, user=self.student_user)
        
        self.parent_user = User.objects.create_user(username='parent_u', password='password123', email='parent@example.com')
        self.parent = Parent.objects.create(user=self.parent_user, student=self.student, phone='9876543210')
        
        self.teacher_user = User.objects.create_user(username='teacher_u', password='password123', email='teacher@example.com')
        self.teacher = Teacher.objects.create(user=self.teacher_user, department='Math')
        self.teacher.assigned_classes.add(self.cls1)
        self.teacher.assigned_subjects.add(self.subj)

        # Other student in Class B (not assigned to teacher)
        self.other_student = Student.objects.create(roll_id='S22', name='Student Two', email='other@example.com', student_class=self.cls2, status=1)

        # Result for Student One
        self.res = Result.objects.create(student=self.student, student_class=self.cls1, subject=self.subj, theory_marks=25, internal_marks=18)

    def test_token_obtain_endpoint(self):
        response = self.client.post(reverse('api_token'), {'username': 'student_u', 'password': 'password123'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())

    def test_api_scoping_admin(self):
        token = Token.objects.create(user=self.admin_user)
        auth_header = f"Token {token.key}"
        
        # Admin gets all students
        response = self.client.get('/api/v1/students/', headers={'Authorization': auth_header})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        # Admin gets all results
        response = self.client.get('/api/v1/results/', headers={'Authorization': auth_header})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_api_scoping_student(self):
        token = Token.objects.create(user=self.student_user)
        auth_header = f"Token {token.key}"
        
        # Student gets only their record
        response = self.client.get('/api/v1/students/', headers={'Authorization': auth_header})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['roll_id'], 'S11')

        # Student gets only their results
        response = self.client.get('/api/v1/results/', headers={'Authorization': auth_header})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_api_scoping_parent(self):
        token = Token.objects.create(user=self.parent_user)
        auth_header = f"Token {token.key}"
        
        # Parent gets only linked student
        response = self.client.get('/api/v1/students/', headers={'Authorization': auth_header})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['roll_id'], 'S11')

    def test_api_scoping_teacher(self):
        token = Token.objects.create(user=self.teacher_user)
        auth_header = f"Token {token.key}"
        
        # Teacher gets only students in Class A (self.cls1)
        response = self.client.get('/api/v1/students/', headers={'Authorization': auth_header})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['roll_id'], 'S11') # Student One is in Class A

    def test_audit_logging_signals(self):
        # Authenticate client to simulate logged in user in middleware
        self.client.login(username='admin_u', password='password123')
        
        # Clear existing logs created in setUp
        AuditLog.objects.all().delete()
        
        # Action that triggers signal (post_save on Student)
        new_stu = Student.objects.create(roll_id='S99', name='New Test Student', email='new@example.com', student_class=self.cls1, status=1)
        
        # Check that AuditLog record exists
        logs = AuditLog.objects.filter(target_model='Student', target_id='S99')
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().action, 'CREATE')

    def test_whatsapp_logging_and_phone_cleaning(self):
        # Run send_whatsapp_message to test validation and logging
        success, msg = send_whatsapp_message('98765 43210', 'Test notice', 'notice')
        
        # Verify log record created with cleaned number '919876543210'
        logs = WhatsAppLog.objects.filter(recipient_number='919876543210')
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().message_type, 'notice')

    def test_admin_audit_log_view_rbac(self):
        # Admin can access audit log page
        self.client.login(username='admin_u', password='password123')
        response = self.client.get(reverse('admin_audit_log'))
        self.assertEqual(response.status_code, 200)

        # Parent is blocked
        self.client.login(username='parent_u', password='password123')
        response = self.client.get(reverse('admin_audit_log'))
        self.assertEqual(response.status_code, 302)

    def test_get_holidays_endpoint(self):
        from resultapp.models import Holiday
        Holiday.objects.create(date='2026-08-15', name='Independence Day')
        Holiday.objects.create(date='2026-09-05', name='Teacher Day')

        # Admin login
        self.client.login(username='admin_u', password='password123')
        response = self.client.get(reverse('get_holidays') + '?from_date=2026-08-01&to_date=2026-08-31')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['holidays']), 1)
        self.assertEqual(data['holidays'][0]['name'], 'Independence Day')

        # Parent login (blocked)
        self.client.login(username='parent_u', password='password123')
        response = self.client.get(reverse('get_holidays') + '?from_date=2026-08-01&to_date=2026-08-31')
        self.assertEqual(response.status_code, 302)

    def test_bulk_attendance_with_custom_exclusions_and_db_save(self):
        # Admin login
        self.client.login(username='admin_u', password='password123')
        
        import json
        from resultapp.models import Holiday, Attendance
        from datetime import date
        
        initial_holidays_count = Holiday.objects.count()
        
        post_data = {
            'mode': 'bulk',
            'class': self.cls1.id,
            'semester': '1',
            'from_date': '2026-08-10',
            'to_date': '2026-08-15',
            'exclude_dates': '2026-08-15,2026-08-12',
            'new_holidays': json.dumps([
                {'date': '2026-08-12', 'name': 'Custom Strike Day'}
            ]),
            f'status_{self.student.id}': 'present',
            f'remarks_{self.student.id}': 'Regular day'
        }
        
        response = self.client.post(reverse('add_attendance'), post_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify custom holiday was saved to the DB
        self.assertEqual(Holiday.objects.count(), initial_holidays_count + 1)
        new_holiday = Holiday.objects.filter(date='2026-08-12').first()
        self.assertIsNotNone(new_holiday)
        self.assertEqual(new_holiday.name, 'Custom Strike Day')
        
        # In range 2026-08-10 (Mon) to 2026-08-15 (Sat):
        # 10th (Mon), 11th (Tue), 12th (Wed), 13th (Thu), 14th (Fri), 15th (Sat) -> 6 calendar days.
        # Excluded dates: 12th (Wed), 15th (Sat).
        # Total working days should be 6 - 2 = 4 working days.
        attendance_records = Attendance.objects.filter(student=self.student)
        self.assertEqual(attendance_records.count(), 4)
        
        # Verify attendance dates
        dates_saved = set(attendance_records.values_list('date', flat=True))
        expected_dates = {
            date(2026, 8, 10),
            date(2026, 8, 11),
            date(2026, 8, 13),
            date(2026, 8, 14),
        }
        self.assertEqual(dates_saved, expected_dates)

    def test_credits_fallback_custom_weight(self):
        """
        Confirm that a subject with credits != 4 uses its real stored credit value
        in get_consolidated_marksheet() and get_sgpa(), not defaulting to 4.
        """
        # Create subjects with credits != 4
        subj_credit2 = Subject.objects.create(subject_name='Seminar', subject_code='SEM201', credits=2)
        subj_credit4 = Subject.objects.create(subject_name='Physics', subject_code='PHY201', credits=4)

        # Clear prior results for student
        Result.objects.filter(student=self.student).delete()

        # Subject 1 (2 credits): Theory 28 + Internal 18 = 46/50 (92%) -> Grade 'O', Grade Point 10
        r1 = Result.objects.create(
            student=self.student, student_class=self.cls1, subject=subj_credit2,
            semester=2, theory_marks=28, internal_marks=18
        )
        # Subject 2 (4 credits): Theory 20 + Internal 13 = 33/50 (66%) -> Grade 'A', Grade Point 8
        r2 = Result.objects.create(
            student=self.student, student_class=self.cls1, subject=subj_credit4,
            semester=2, theory_marks=20, internal_marks=13
        )

        marksheet = self.student.get_consolidated_marksheet(semester=2)
        # Total credits: 2 + 4 = 6
        self.assertEqual(marksheet['total_credits'], 6)
        # Verify individual subject row credit value
        sem_row = next(s for s in marksheet['subjects'] if s['subject_code'] == 'SEM201')
        self.assertEqual(sem_row['credits'], 2)

        # SGPA: (2 * 10 + 4 * 8) / (2 + 4) = (20 + 32) / 6 = 52 / 6 = 8.67
        # Note: If credits=2 was incorrectly forced to 4, SGPA would be (4*10 + 4*8)/8 = 9.00
        self.assertEqual(marksheet['sgpa'], 8.67)

    def test_edit_result_component_marks_persistence(self):
        """
        Confirm edit_result correctly saves individual component marks (theory, internal, practical, oral)
        and updates self.marks = self.total_obtained in sync.
        """
        self.client.login(username='admin_u', password='password123')
        post_data = {
            'id[]': [self.res.id],
            f'theory_{self.res.id}': '26',     # max 30
            f'internal_{self.res.id}': '18',   # max 20
            f'practical_{self.res.id}': '22',  # max 25
            f'oral_{self.res.id}': '20',       # max 25
        }
        response = self.client.post(reverse('edit_result', kwargs={'stid': self.student.id}), post_data)
        self.assertEqual(response.status_code, 302)

        self.res.refresh_from_db()
        self.assertEqual(self.res.theory_marks, 26)
        self.assertEqual(self.res.internal_marks, 18)
        self.assertEqual(self.res.practical_marks, 22)
        self.assertEqual(self.res.oral_marks, 20)
        # Total: 26 + 18 + 22 + 20 = 86
        self.assertEqual(self.res.total_obtained, 86)
        self.assertEqual(self.res.marks, 86)

    def test_class_cascade_populates_only_class_subjects_and_semester(self):
        """
        Verify: (a) selecting a Class populates only that class's actual subjects and valid semesters.
        """
        self.client.login(username='admin_u', password='password123')

        branch = Branch.objects.create(branch_name='Computer Science', branch_code='CS_TEST', status=1)
        fycs = Class.objects.create(branch=branch, class_name='First Year CS', class_numeric=1, section='A')
        sycs = Class.objects.create(branch=branch, class_name='Second Year CS', class_numeric=2, section='A')

        # Create subjects across Semesters 1, 2, 3, 4
        s1 = Subject.objects.create(subject_name='FY Sem 1 Subj', subject_code='CS101', credits=4)
        s2 = Subject.objects.create(subject_name='FY Sem 2 Subj', subject_code='CS201', credits=4)
        s3 = Subject.objects.create(subject_name='SY Sem 3 Subj', subject_code='CS301', credits=4)
        s4 = Subject.objects.create(subject_name='SY Sem 4 Subj', subject_code='CS401', credits=4)

        BranchSubject.objects.create(branch=branch, subject=s1, semester=1, status=1)
        BranchSubject.objects.create(branch=branch, subject=s2, semester=2, status=1)
        BranchSubject.objects.create(branch=branch, subject=s3, semester=3, status=1)
        BranchSubject.objects.create(branch=branch, subject=s4, semester=4, status=1)

        # FYCS only has Sem 1 & 2 subjects
        SubjectCombination.objects.create(student_class=fycs, subject=s1, status=1)
        SubjectCombination.objects.create(student_class=fycs, subject=s2, status=1)

        # SYCS only has Sem 3 & 4 subjects
        SubjectCombination.objects.create(student_class=sycs, subject=s3, status=1)
        SubjectCombination.objects.create(student_class=sycs, subject=s4, status=1)

        # Test selecting SYCS without semester filter: should return semesters [3, 4] and ONLY s3 and s4
        url = reverse('get_students_subjects') + f'?class_id={sycs.id}'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['semesters'], [3, 4])

        returned_subject_ids = [s['id'] for s in data['subjects']]
        self.assertIn(s3.id, returned_subject_ids)
        self.assertIn(s4.id, returned_subject_ids)
        self.assertNotIn(s1.id, returned_subject_ids)
        self.assertNotIn(s2.id, returned_subject_ids)

        # Test selecting SYCS with semester=3: should return ONLY s3
        url_sem3 = reverse('get_students_subjects') + f'?class_id={sycs.id}&semester=3'
        res_sem3 = self.client.get(url_sem3)
        self.assertEqual(res_sem3.status_code, 200)
        data_sem3 = res_sem3.json()
        sem3_ids = [s['id'] for s in data_sem3['subjects']]
        self.assertEqual(sem3_ids, [s3.id])

    def test_bulk_attendance_atomic_performance_and_query_count(self):
        """
        Verify: (b) a bulk submit across a multi-day range creates the correct number of
        Attendance rows in a single efficient DB operation (assert query count bounded).
        """
        from datetime import date
        self.client.login(username='admin_u', password='password123')

        test_class = Class.objects.create(class_name='Bulk Test Class', class_numeric=11, section='A')
        test_students = []
        for i in range(5):
            st = Student.objects.create(
                roll_id=f'BULK_{i}', name=f'Bulk Student {i}',
                email=f'bulk_{i}@example.com', student_class=test_class, status=1
            )
            test_students.append(st)

        # 5 working days: 2026-09-14 (Mon) to 2026-09-18 (Fri)
        from_date = '2026-09-14'
        to_date   = '2026-09-18'

        post_data = {
            'class': test_class.id,
            'from_date': from_date,
            'to_date': to_date,
            'exclude_dates': '',
            'new_holidays': '',
        }
        for st in test_students:
            post_data[f'status_{st.id}'] = 'present'
            post_data[f'remarks_{st.id}'] = ''

        # The bulk submit of 5 students across 5 days = 25 Attendance records.
        # Query count during the POST is tightly bounded to 10 queries total (including auth/session).
        with self.assertNumQueries(10):
            response = self.client.post(reverse('add_attendance'), post_data)
        self.assertEqual(response.status_code, 302)

        # Verify correct number of Attendance rows created
        created_count = Attendance.objects.filter(student__in=test_students).count()
        self.assertEqual(created_count, 5 * 5)  # 25 rows

        # Verify all 5 dates were recorded
        expected_dates = {
            date(2026, 9, 14), date(2026, 9, 15), date(2026, 9, 16),
            date(2026, 9, 17), date(2026, 9, 18)
        }
        actual_dates = set(Attendance.objects.filter(student__in=test_students).values_list('date', flat=True))
        self.assertEqual(actual_dates, expected_dates)

        # Now test bulk_update: update all 5 students across the same 5 days to absent
        for st in test_students:
            post_data[f'status_{st.id}'] = 'absent'
            post_data[f'remarks_{st.id}'] = 'Sick leave'

        # Query count is bounded (under 12 queries total including Parent email alert lookup)
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(reverse('add_attendance'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertLessEqual(len(ctx), 12)

        # Row count should still be 25 (updated in place, not duplicated)
        self.assertEqual(Attendance.objects.filter(student__in=test_students).count(), 25)
        # All statuses should now be absent
        absent_count = Attendance.objects.filter(student__in=test_students, status='absent').count()
        self.assertEqual(absent_count, 25)

    def test_parent_portal_rbac_isolation(self):
        """
        Verify that a logged-in parent can only see their own child's data
        across dashboard, results, attendance, exams, and consolidated marksheet.
        """
        # Create second student and second parent
        student2_user = User.objects.create_user(username='student2_u', password='password123', email='student2@example.com')
        student2 = Student.objects.create(roll_id='S22_UNIQUE', name='Secret Student Two', email='student2@example.com', student_class=self.cls2, status=1, user=student2_user)
        parent2_user = User.objects.create_user(username='parent2_u', password='password123', email='parent2@example.com')
        parent2 = Parent.objects.create(user=parent2_user, student=student2, phone='9876543211', relationship='mother')

        # Create distinct results and attendance for Student 2
        subj2 = Subject.objects.create(subject_name='Secret Physics', subject_code='PHY999', credits=4)
        Result.objects.create(student=student2, student_class=self.cls2, subject=subj2, theory_marks=28, internal_marks=19)
        from datetime import date
        Attendance.objects.create(student=student2, date=date(2026, 9, 20), status='present')

        # Log in as Parent 1
        self.client.login(username='parent_u', password='password123')

        # 1. Dashboard
        resp = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.student.name)
        self.assertContains(resp, self.student.roll_id)
        self.assertNotContains(resp, 'Secret Student Two')
        self.assertNotContains(resp, 'S22_UNIQUE')

        # 2. Results
        resp = self.client.get(reverse('parent_results'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.subj.subject_name)
        self.assertNotContains(resp, 'Secret Physics')
        self.assertNotContains(resp, 'PHY999')

        # 3. Attendance
        resp = self.client.get(reverse('parent_attendance'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.student.name)
        self.assertNotContains(resp, 'Secret Student Two')

        # 4. Consolidated Marksheet
        resp = self.client.get(reverse('parent_consolidated_marksheet'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.student.name)
        self.assertNotContains(resp, 'Secret Student Two')

        # 5. Upcoming Exams
        resp = self.client.get(reverse('parent_exams'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.student.name)
        self.assertNotContains(resp, 'Secret Student Two')

        # Now log out and log in as Parent 2
        self.client.logout()
        self.client.login(username='parent2_u', password='password123')

        resp2 = self.client.get(reverse('parent_dashboard'))
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, 'Secret Student Two')
        self.assertContains(resp2, 'S22_UNIQUE')
        self.assertNotContains(resp2, self.student.name)
        self.assertNotContains(resp2, self.student.roll_id)



