"""
One-off seed script — creates a demo Class, Subjects, Student, Results,
and a Parent login so you can click around the freshly-styled site.

Run with:
    python manage.py shell < scripts/seed_demo_data.py
"""
from django.contrib.auth.models import User
from resultapp.models import Class, Subject, SubjectCombination, Student, Result, Parent

print("Seeding demo data...")

# ── Class ──────────────────────────────────────────────
klass, _ = Class.objects.get_or_create(
    class_name="Class 10", class_numeric=10, section="A"
)

# ── Subjects ───────────────────────────────────────────
subjects_data = [
    ("Mathematics", "MATH101"),
    ("Science", "SCI101"),
    ("English", "ENG101"),
]
subjects = []
for name, code in subjects_data:
    subj, _ = Subject.objects.get_or_create(subject_name=name, subject_code=code)
    subjects.append(subj)
    SubjectCombination.objects.get_or_create(student_class=klass, subject=subj)

# ── Student ────────────────────────────────────────────
student, created = Student.objects.get_or_create(
    roll_id="STU2026001",
    defaults=dict(
        name="Rahul Sharma",
        email="rahul.sharma.demo@example.com",
        gender="male",
        dob="2010-05-14",
        student_class=klass,
        status=1,
    ),
)
if not created:
    student.name = "Rahul Sharma"
    student.student_class = klass
    student.save()

# ── Results (NEP 2020 style: theory /30, internal /20) ──
marks_plan = {
    "MATH101": (27, 18),
    "SCI101":  (25, 17),
    "ENG101":  (24, 16),
}
for subj in subjects:
    theory, internal = marks_plan[subj.subject_code]
    Result.objects.update_or_create(
        student=student, subject=subj,
        defaults=dict(
            student_class=klass,
            theory_marks=theory,
            internal_marks=internal,
        ),
    )

# ── Parent account ──────────────────────────────────────
parent_username = "rahul.parent"
parent_password = "ParentDemo@123"

parent_user, user_created = User.objects.get_or_create(
    username=parent_username,
    defaults=dict(
        first_name="Suresh",
        last_name="Sharma",
        email="suresh.sharma.demo@example.com",
    ),
)
parent_user.set_password(parent_password)
parent_user.save()

Parent.objects.get_or_create(
    user=parent_user,
    defaults=dict(
        phone="9876543210",
        address="12 MG Road, Mumbai",
        student=student,
        relationship="father",
    ),
)

print("=" * 60)
print("Demo data ready:")
print(f"  Class:   {klass}")
print(f"  Student: {student.name}  (roll no. {student.roll_id})")
print(f"  Results: {', '.join(f'{s.subject_name}' for s in subjects)} added")
print(f"  Parent login  ->  username: {parent_username}  password: {parent_password}")
print("=" * 60)
