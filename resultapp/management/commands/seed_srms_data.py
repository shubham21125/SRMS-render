import random
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User

from resultapp.models import (
    Branch, Class, Subject, BranchSubject, SubjectCombination,
    Student, Result, Attendance, Parent, ProgressReport, Exam, Holiday
)
import resultapp.signals as srms_signals


class Command(BaseCommand):
    help = "Seed realistic, production-grade test data for SRMS (Results, 2-Month Attendance, Parents, Progress Reports, Upcoming Exams)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Wipe prior generated attendance, progress reports, exams, and parent accounts before re-seeding.',
        )

    def handle(self, *args, **options):
        random.seed(42)
        clear_first = options.get('clear', False)

        self.stdout.write(self.style.MIGRATE_HEADING("=== Starting SRMS Realistic Data Seeder ==="))

        classes = list(Class.objects.all().order_by('id'))
        if not classes:
            self.stderr.write("No classes found. Please run migrations first.")
            return

        students = list(Student.objects.all().select_related('student_class').order_by('id'))
        self.stdout.write(f"Found {len(classes)} classes and {len(students)} students.")

        # Disconnect audit signals during bulk seed to prevent 10,000+ redundant log entries
        post_save.disconnect(srms_signals.log_student_save, sender=Student)
        post_delete.disconnect(srms_signals.log_student_delete, sender=Student)
        post_save.disconnect(srms_signals.log_result_save, sender=Result)
        post_delete.disconnect(srms_signals.log_result_delete, sender=Result)

        try:
            # ─────────────────────────────────────────────────────────────
            # 1. SEED / UPDATE RESULTS (Subject-wise with NEP 2020 components)
            # ─────────────────────────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[1/5] Seeding Results for all students..."))
            
            # Map class -> applicable semesters
            # Class numeric 1 -> Sems [1, 2], 2 -> [3, 4], 3 -> [5, 6]
            class_sem_map = {
                1: [1, 2],
                2: [3, 4],
                3: [5, 6]
            }

            # Map (branch_id, semester) -> subjects
            branch_subjs = BranchSubject.objects.filter(status=1).select_related('subject', 'branch')
            sem_subjects_map = {}
            for bs in branch_subjs:
                sem_subjects_map.setdefault((bs.branch_id, bs.semester), []).append(bs.subject)

            # Clear existing results if --clear
            if clear_first:
                deleted_results, _ = Result.objects.all().delete()
                self.stdout.write(f"  Cleared {deleted_results} prior results.")

            # Map existing results (student_id, subject_id, semester)
            existing_results = {
                (r.student_id, r.subject_id, r.semester): r
                for r in Result.objects.all()
            }

            results_to_create = []
            results_to_update = []

            for student in students:
                cls = student.student_class
                if not cls:
                    continue

                numeric = cls.class_numeric
                applicable_sems = class_sem_map.get(numeric, [1, 2])
                branch_id = cls.branch_id

                for sem in applicable_sems:
                    subjects = sem_subjects_map.get((branch_id, sem), [])
                    for subj in subjects:
                        key = (student.id, subj.id, sem)
                        existing_r = existing_results.get(key)

                        # Generate realistic marks:
                        # 85% pass rate with realistic grade distribution
                        is_high_performer = (student.id % 5 == 0)
                        is_struggling = (student.id % 23 == 0)

                        if is_high_performer:
                            theory = random.randint(24, 30)
                            internal = random.randint(16, 20)
                            practical = random.randint(20, 25)
                            oral = random.randint(20, 25)
                        elif is_struggling:
                            theory = random.randint(9, 14)    # occasional fail under 12
                            internal = random.randint(6, 11)   # occasional fail under 8
                            practical = random.randint(8, 14)
                            oral = random.randint(8, 14)
                        else:
                            theory = random.randint(14, 27)
                            internal = random.randint(10, 18)
                            practical = random.randint(14, 22)
                            oral = random.randint(14, 22)

                        # Check if subject is practical/oral oriented (programming/systems)
                        code = subj.subject_code or ""
                        has_practical = any(c in code for c in ['CS101', 'CS103', 'CS202', 'CS204', 'CS301', 'CS304', 'CS401', 'CS402', 'CS501', 'CS503', 'CS601', 'CS602'])
                        p_val = practical if has_practical else None
                        o_val = oral if (has_practical and random.random() > 0.5) else None

                        total_obt = theory + internal + (p_val or 0) + (o_val or 0)

                        if existing_r:
                            existing_r.theory_marks = theory
                            existing_r.internal_marks = internal
                            existing_r.practical_marks = p_val
                            existing_r.oral_marks = o_val
                            existing_r.marks = total_obt
                            existing_r.student_class = cls
                            results_to_update.append(existing_r)
                        else:
                            results_to_create.append(Result(
                                student=student,
                                student_class=cls,
                                subject=subj,
                                semester=sem,
                                theory_marks=theory,
                                internal_marks=internal,
                                practical_marks=p_val,
                                oral_marks=o_val,
                                marks=total_obt
                            ))

            with transaction.atomic():
                if results_to_create:
                    Result.objects.bulk_create(results_to_create, batch_size=1000)
                if results_to_update:
                    Result.objects.bulk_update(
                        results_to_update,
                        ['theory_marks', 'internal_marks', 'practical_marks', 'oral_marks', 'marks', 'student_class'],
                        batch_size=1000
                    )

            total_res_count = Result.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Results up to date: {total_res_count} total records across {len(students)} students."))

            # ─────────────────────────────────────────────────────────────
            # 2. BULK SEED ATTENDANCE (Last 2 Calendar Months, ~90% present)
            # ─────────────────────────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[2/5] Seeding 2-month bulk attendance..."))
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=60) # ~2 calendar months

            # Collect dates skipping Sundays and standard holidays
            holidays_set = {
                date(2026, 8, 15), # Independence Day
                date(2026, 8, 27), # Raksha Bandhan
                date(2026, 9, 7),  # Ganesh Chaturthi
            }
            # Also save these holidays to Holiday model if not present
            Holiday.objects.get_or_create(date=date(2026, 8, 15), defaults={'name': 'Independence Day'})
            Holiday.objects.get_or_create(date=date(2026, 8, 27), defaults={'name': 'Raksha Bandhan'})
            Holiday.objects.get_or_create(date=date(2026, 9, 7),  defaults={'name': 'Ganesh Chaturthi'})

            working_dates = []
            cur_d = start_date
            while cur_d <= end_date:
                if cur_d.weekday() != 6 and cur_d not in holidays_set: # skip Sundays (6)
                    working_dates.append(cur_d)
                cur_d += timedelta(days=1)

            self.stdout.write(f"  Working dates in range ({start_date} to {end_date}): {len(working_dates)} days.")

            # Clear existing attendance for these students to make distribution clean
            if clear_first:
                Attendance.objects.all().delete()
                self.stdout.write("  Cleared all prior attendance records.")
            else:
                Attendance.objects.filter(student__in=students, date__gte=start_date).delete()

            # Pre-assign individual attendance profiles per student:
            # - 80% of students have ~93% attendance
            # - 15% of students have ~85% attendance
            # - 5% of students have an illness streak (~70% attendance)
            attendance_records = []
            for st in students:
                profile_roll = random.random()
                if profile_roll < 0.75:
                    p_present = 0.94
                elif profile_roll < 0.92:
                    p_present = 0.86
                else:
                    p_present = 0.72

                streak_days = 0
                for d in working_dates:
                    if streak_days > 0:
                        status = 'absent'
                        streak_days -= 1
                    else:
                        if random.random() < p_present:
                            status = 'present'
                        else:
                            status = 'absent'
                            # 25% chance of starting a 2-day streak
                            if random.random() < 0.25:
                                streak_days = 1

                    rem = 'Sick leave' if (status == 'absent' and random.random() < 0.3) else ''
                    attendance_records.append(Attendance(
                        student=st,
                        subject=None, # General daily attendance
                        semester=None,
                        date=d,
                        status=status,
                        remarks=rem
                    ))

            with transaction.atomic():
                Attendance.objects.bulk_create(attendance_records, batch_size=2000)

            att_count = Attendance.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Attendance seeded: {len(attendance_records)} records saved. Total attendance rows: {att_count}."))

            # ─────────────────────────────────────────────────────────────
            # 3. SEED PARENT ACCOUNTS (For all students without a linked parent)
            # ─────────────────────────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[3/5] Seeding Parent accounts..."))

            existing_parents = {p.student_id: p for p in Parent.objects.all().select_related('user')}
            parents_created = 0

            parent_first_names = [
                "Rajesh", "Suresh", "Ramesh", "Mahesh", "Dinesh", "Ganesh", "Vijay", "Anand",
                "Sunita", "Shobha", "Rekha", "Anita", "Kavita", "Sangeeta", "Meena", "Geeta",
                "Deepak", "Prakash", "Sanjay", "Vinod", "Ashok", "Kishore", "Arun", "Manoj"
            ]

            relationships = ['father', 'mother', 'guardian']

            for st in students:
                if st.id in existing_parents:
                    continue

                clean_roll = st.roll_id.replace('-', '_').replace(' ', '').lower()
                username = f"parent_{clean_roll}"
                email = f"parent_{clean_roll}@example.com"

                # Check if User already exists
                user = User.objects.filter(username=username).first()
                if not user:
                    p_fname = random.choice(parent_first_names)
                    p_lname = st.name.split()[-1] if ' ' in st.name else "Parent"
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=p_fname,
                        last_name=p_lname
                    )
                    user.set_password("Parent@123")
                    user.save()

                phone = f"+9198{random.randint(10000000, 99999999)}"
                rel = random.choices(relationships, weights=[50, 45, 5])[0]

                Parent.objects.create(
                    user=user,
                    student=st,
                    phone=phone,
                    relationship=rel,
                    email_alerts=True
                )
                parents_created += 1

            total_parents = Parent.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Parent accounts: {parents_created} created. Total parents in system: {total_parents} (all linked)."))
            self.stdout.write("    (Credentials for all parents: Username `parent_<roll_id>` / Password `Parent@123`)")

            # ─────────────────────────────────────────────────────────────
            # 4. SEED PROGRESS REPORTS (1 record per student for Term 1)
            # ─────────────────────────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[4/5] Seeding Progress Reports..."))

            term_name = "Term 1 - Academic Year 2026-27"
            if clear_first:
                ProgressReport.objects.filter(term=term_name).delete()

            existing_pr = set(ProgressReport.objects.filter(term=term_name).values_list('student_id', flat=True))
            reports_to_create = []

            remarks_templates = [
                ("Consistent dedication to technical lab work. Shows strong initiative in group projects.", "Data structures, problem solving, teamwork", "Time management during long theory essays"),
                ("Demonstrates keen curiosity in algorithm design. High participation in lecture discussions.", "Analytical reasoning, mathematics, focus", "Documentation formatting in lab journals"),
                ("Steady academic progress with excellent conceptual retention across all subjects.", "Database normalization, Python scripting", "Participation in extracurricular tech seminars"),
                ("Good grasp of computer systems architecture. Very polite and disciplined in class.", "System architecture, code syntax, punctuality", "Needs to practice more dynamic programming problems"),
                ("Exceptional programming fluency and clean code aesthetics. Top tier performance.", "Full stack concepts, algorithm efficiency, leadership", "None noted; maintain current standard")
            ]

            for st in students:
                if st.id in existing_pr:
                    continue

                # Calculate overall % from results if available
                res_objs = Result.objects.filter(student=st)
                if res_objs.exists():
                    total_obt = sum(r.total_obtained for r in res_objs)
                    total_max = sum(r.total_max for r in res_objs)
                    overall_pct = round((total_obt / total_max * 100), 2) if total_max > 0 else 75.0
                else:
                    overall_pct = round(random.uniform(68.0, 92.0), 2)

                if overall_pct >= 80:
                    grade = 'O'
                elif overall_pct >= 70:
                    grade = 'A+'
                elif overall_pct >= 60:
                    grade = 'A'
                else:
                    grade = 'B+'

                remark, strength, improvement = random.choice(remarks_templates)

                reports_to_create.append(ProgressReport(
                    student=st,
                    term=term_name,
                    overall_percentage=overall_pct,
                    grade=grade,
                    teacher_remarks=remark,
                    strengths=strength,
                    areas_of_improvement=improvement
                ))

            if reports_to_create:
                ProgressReport.objects.bulk_create(reports_to_create, batch_size=500)

            total_pr = ProgressReport.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Progress Reports: {len(reports_to_create)} created. Total reports: {total_pr}."))

            # ─────────────────────────────────────────────────────────────
            # 5. SEED UPCOMING EXAMS (Future dates relative to today)
            # ─────────────────────────────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n[5/5] Seeding Upcoming Exams..."))

            # Wipe old/past exams
            Exam.objects.all().delete()

            exam_schedule = [
                # Class 13 (FYCS)
                (13, "CS101", date(2026, 10, 14), "Mid-Term Theory Exam — Digital Systems"),
                (13, "CS102", date(2026, 10, 16), "Mid-Term Theory Exam — Database Systems"),
                (13, "CS103", date(2026, 10, 20), "Practical Lab Evaluation — Python Programming"),
                (13, "CS104", date(2026, 11, 10), "Semester End Exam — Communication Skills"),
                # Class 14 (SYCS)
                (14, "CS301", date(2026, 10, 15), "Mid-Term Theory Exam — Operating Systems"),
                (14, "CS303", date(2026, 10, 18), "Mid-Term Theory Exam — DBMS & SQL"),
                (14, "CS304", date(2026, 10, 22), "Practical Lab Viva — Core Java Programming"),
                (14, "CS302", date(2026, 11, 12), "Semester End Exam — Combinatorics & Graph Theory"),
                # Class 15 (TYCS)
                (15, "CS501", date(2026, 10, 14), "Mid-Term Assessment — Artificial Intelligence"),
                (15, "CS502", date(2026, 10, 17), "Mid-Term Assessment — Network Security"),
                (15, "CS503", date(2026, 10, 21), "Practical Lab Exam — Linux Server Administration"),
                (15, "CS504", date(2026, 11, 15), "Semester End Exam — Software Testing & QA"),
            ]

            exams_created = 0
            for class_id, subj_code, ex_date, title in exam_schedule:
                cls_obj = Class.objects.filter(id=class_id).first()
                subj_obj = Subject.objects.filter(subject_code=subj_code).first()
                if cls_obj and subj_obj:
                    Exam.objects.create(
                        student_class=cls_obj,
                        subject=subj_obj,
                        exam_date=ex_date,
                        title=title
                    )
                    exams_created += 1

            self.stdout.write(self.style.SUCCESS(f"  [OK] Upcoming Exams: {exams_created} scheduled across all 3 classes."))

        finally:
            # Reconnect signals
            post_save.connect(srms_signals.log_student_save, sender=Student)
            post_delete.connect(srms_signals.log_student_delete, sender=Student)
            post_save.connect(srms_signals.log_result_save, sender=Result)
            post_delete.connect(srms_signals.log_result_delete, sender=Result)

        self.stdout.write(self.style.SUCCESS("\n=== SRMS Data Seeding Completed Successfully! ==="))
