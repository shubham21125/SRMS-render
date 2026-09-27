import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_DIR)

import django
import sqlite3
import json
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StudentResultManagement.settings')
django.setup()

from django.apps import apps
from django.db import connection
from django.contrib.auth.models import User
from resultapp.models import (
    Branch, Class, Subject, BranchSubject, Student, SubjectCombination,
    Result, Notice, Holiday, Parent, Attendance, ProgressReport,
    Teacher, AdminProfile, Exam, AuditLog, WhatsAppLog
)

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

print("="*80)
print("1. ALL 31 TABLES AND EXACT ROW COUNTS")
print("="*80)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
all_tables = [r[0] for r in cur.fetchall()]
for t in all_tables:
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    print(f"  {t:45} : {cnt} rows")

print("\n" + "="*80)
print("2. INVESTIGATION 1: EMPTY TABLES (0 rows)")
print("="*80)
empty_tables = [t for t in all_tables if cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] == 0]
print("Empty tables:", empty_tables)

# Check Holiday save path in codebase
print("\n--- Holiday usage check ---")
from resultapp.models import Holiday
print(f"Holiday count: {Holiday.objects.count()}")

# Check WhatsAppLog usage in codebase
print("\n--- WhatsAppLog usage check ---")
print(f"WhatsAppLog count: {WhatsAppLog.objects.count()}")

# Check ProgressReport usage in codebase
print("\n--- ProgressReport usage check ---")
print(f"ProgressReport count: {ProgressReport.objects.count()}")

# Check auth tables
print("\n--- Auth / Django builtins check ---")
cur.execute("SELECT COUNT(*) FROM auth_user")
print(f"auth_user: {cur.fetchone()[0]} rows")
cur.execute("SELECT COUNT(*) FROM auth_group")
print(f"auth_group: {cur.fetchone()[0]} rows")
cur.execute("SELECT COUNT(*) FROM authtoken_token")
print(f"authtoken_token: {cur.fetchone()[0]} rows")

print("\n" + "="*80)
print("3. INVESTIGATION 2: REDUNDANT / OVERLAPPING TABLES")
print("="*80)
print(f"Subject count: {Subject.objects.count()}")
print(f"BranchSubject count: {BranchSubject.objects.count()}")
print(f"SubjectCombination count: {SubjectCombination.objects.count()}")

# Detail on Subject, BranchSubject, SubjectCombination
print("\nSample BranchSubject:")
for bs in BranchSubject.objects.select_related('branch', 'subject')[:5]:
    print(f"  Branch: {bs.branch.branch_code}, Subject: {bs.subject.subject_code} ({bs.subject.subject_name}), Sem: {bs.semester}")

print("\nSample SubjectCombination:")
for sc in SubjectCombination.objects.select_related('student_class', 'subject')[:5]:
    print(f"  Class: {sc.student_class}, Subject: {sc.subject.subject_code} ({sc.subject.subject_name})")

print("\nTeacher M2M tables:")
cur.execute("SELECT * FROM resultapp_teacher_assigned_classes")
print("  teacher_assigned_classes:", cur.fetchall())
cur.execute("SELECT * FROM resultapp_teacher_assigned_subjects")
print("  teacher_assigned_subjects:", cur.fetchall())

print("\n" + "="*80)
print("4. INVESTIGATION 3: AUDITLOG")
print("="*80)
cur.execute("SELECT COUNT(*), action, target_model FROM resultapp_auditlog GROUP BY action, target_model")
for row in cur.fetchall():
    print(f"  Action: {row[1]}, Target: {row[2]}, Count: {row[0]}")
cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM resultapp_auditlog")
min_t, max_t = cur.fetchone()
print(f"  Timestamp range: {min_t} to {max_t}")

print("\n" + "="*80)
print("5. INVESTIGATION 4: ROW-COUNT SANITY CHECKS")
print("="*80)
print(f"Student count: {Student.objects.count()}")
print(f"Result count: {Result.objects.count()}")
print(f"Attendance count: {Attendance.objects.count()}")

# Check for Result rows with NULL / 0 marks
null_or_zero_results = Result.objects.filter(theory_marks=0, internal_marks=0)
print(f"Results with theory=0 and internal=0: {null_or_zero_results.count()}")
null_components = Result.objects.filter(theory_marks__isnull=True)
print(f"Results with theory is NULL: {null_components.count()}")

# Check students per class
print("\nStudents per class:")
for c in Class.objects.all():
    st_count = Student.objects.filter(student_class=c).count()
    res_count = Result.objects.filter(student_class=c).count()
    print(f"  Class {c.id}: '{c.class_name}' ({c.branch}) -> Students: {st_count}, Results: {res_count}")

# Check attendance breakdown
print("\nAttendance dates count:", Attendance.objects.values('date').distinct().count())
print("Attendance students count:", Attendance.objects.values('student').distinct().count())

print("\n" + "="*80)
print("6. PART A: CLASS FOREIGN KEY USAGE ANALYSIS (IDs 1, 9, 10, 11, 12, 13, 14, 15)")
print("="*80)
for c in Class.objects.all():
    print(f"\nAnalyzing Class ID {c.id}: '{c.class_name}', branch={c.branch_id}, numeric={c.class_numeric}, section='{c.section}'")
    # Student
    st_c = Student.objects.filter(student_class=c).count()
    # Result
    res_c = Result.objects.filter(student_class=c).count()
    # SubjectCombination
    sc_c = SubjectCombination.objects.filter(student_class=c).count()
    # Exam
    ex_c = Exam.objects.filter(student_class=c).count()
    # Teacher assigned classes
    cur.execute("SELECT COUNT(*) FROM resultapp_teacher_assigned_classes WHERE class_id = ?", (c.id,))
    t_c = cur.fetchone()[0]
    print(f"  Students: {st_c}, Results: {res_c}, SubjectCombination: {sc_c}, Exam: {ex_c}, TeacherAssigned: {t_c}")

print("\n" + "="*80)
print("7. ORPHANED FOREIGN KEYS CHECK")
print("="*80)
# Check orphaned Result -> Student
cur.execute("SELECT COUNT(*) FROM resultapp_result WHERE student_id NOT IN (SELECT id FROM resultapp_student)")
print(f"Orphaned Result -> Student: {cur.fetchone()[0]}")
# Check orphaned Result -> Subject
cur.execute("SELECT COUNT(*) FROM resultapp_result WHERE subject_id IS NOT NULL AND subject_id NOT IN (SELECT id FROM resultapp_subject)")
print(f"Orphaned Result -> Subject: {cur.fetchone()[0]}")
# Check orphaned Result -> Class
cur.execute("SELECT COUNT(*) FROM resultapp_result WHERE student_class_id IS NOT NULL AND student_class_id NOT IN (SELECT id FROM resultapp_class)")
print(f"Orphaned Result -> Class: {cur.fetchone()[0]}")
# Check orphaned Student -> Class
cur.execute("SELECT COUNT(*) FROM resultapp_student WHERE student_class_id IS NOT NULL AND student_class_id NOT IN (SELECT id FROM resultapp_class)")
print(f"Orphaned Student -> Class: {cur.fetchone()[0]}")
# Check orphaned Student -> User
cur.execute("SELECT COUNT(*) FROM resultapp_student WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM auth_user)")
print(f"Orphaned Student -> User: {cur.fetchone()[0]}")
# Check orphaned Attendance -> Student
cur.execute("SELECT COUNT(*) FROM resultapp_attendance WHERE student_id NOT IN (SELECT id FROM resultapp_student)")
print(f"Orphaned Attendance -> Student: {cur.fetchone()[0]}")
# Check orphaned Attendance -> Subject
cur.execute("SELECT COUNT(*) FROM resultapp_attendance WHERE subject_id IS NOT NULL AND subject_id NOT IN (SELECT id FROM resultapp_subject)")
print(f"Orphaned Attendance -> Subject: {cur.fetchone()[0]}")
# Check orphaned Parent -> Student
cur.execute("SELECT COUNT(*) FROM resultapp_parent WHERE student_id NOT IN (SELECT id FROM resultapp_student)")
print(f"Orphaned Parent -> Student: {cur.fetchone()[0]}")
# Check orphaned Parent -> User
cur.execute("SELECT COUNT(*) FROM resultapp_parent WHERE user_id NOT IN (SELECT id FROM auth_user)")
print(f"Orphaned Parent -> User: {cur.fetchone()[0]}")
# Check orphaned BranchSubject -> Branch
cur.execute("SELECT COUNT(*) FROM resultapp_branchsubject WHERE branch_id NOT IN (SELECT id FROM resultapp_branch)")
print(f"Orphaned BranchSubject -> Branch: {cur.fetchone()[0]}")
# Check orphaned BranchSubject -> Subject
cur.execute("SELECT COUNT(*) FROM resultapp_branchsubject WHERE subject_id NOT IN (SELECT id FROM resultapp_subject)")
print(f"Orphaned BranchSubject -> Subject: {cur.fetchone()[0]}")
# Check orphaned SubjectCombination -> Class
cur.execute("SELECT COUNT(*) FROM resultapp_subjectcombination WHERE student_class_id IS NOT NULL AND student_class_id NOT IN (SELECT id FROM resultapp_class)")
print(f"Orphaned SubjectCombination -> Class: {cur.fetchone()[0]}")
# Check orphaned SubjectCombination -> Subject
cur.execute("SELECT COUNT(*) FROM resultapp_subjectcombination WHERE subject_id IS NOT NULL AND subject_id NOT IN (SELECT id FROM resultapp_subject)")
print(f"Orphaned SubjectCombination -> Subject: {cur.fetchone()[0]}")
# Check orphaned Exam -> Class
cur.execute("SELECT COUNT(*) FROM resultapp_exam WHERE student_class_id NOT IN (SELECT id FROM resultapp_class)")
print(f"Orphaned Exam -> Class: {cur.fetchone()[0]}")
# Check orphaned Exam -> Subject
cur.execute("SELECT COUNT(*) FROM resultapp_exam WHERE subject_id NOT IN (SELECT id FROM resultapp_subject)")
print(f"Orphaned Exam -> Subject: {cur.fetchone()[0]}")

print("\n" + "="*80)
print("8. PRAGMA foreign_keys CHECK")
print("="*80)
cur.execute("PRAGMA foreign_keys;")
print(f"SQLite PRAGMA foreign_keys status: {cur.fetchone()[0]}")
