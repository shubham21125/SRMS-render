# SRMS Database Schema Audit Report

**Date:** September 25, 2026  
**Environment:** SQLite 3 (`db.sqlite3`), Django 4.2.30  
**Scope:** Complete inspection of all 31 database tables, column structures, constraints, foreign key integrity, indexes, triggers, and data distributions.

---

## 1. Executive Summary & Inventory of All 31 Tables

The SQLite database contains **31 tables** consisting of:
- **17 application tables** (`resultapp_*`)
- **10 Django auth / admin / content-type tables**
- **1 session table** (`django_session`)
- **1 migration history table** (`django_migrations`)
- **1 authtoken table** (`authtoken_token`)
- **1 SQLite internal sequence table** (`sqlite_sequence`)

### Complete Table Inventory & Row Counts

| Table Name | Category | Row Count | Status / Notes |
|:---|:---|:---:|:---|
| `resultapp_adminprofile` | Application | 1 | Admin profile extension (photo, dates) |
| `resultapp_attendance` | Application | 88 | Pre-seed test attendance records for Student 1 |
| `resultapp_auditlog` | Application | 1,354 | Automated signal-based audit log for Student & Result ops |
| `resultapp_branch` | Application | 2 | Academic programmes (`BSCCS` active; `CS101` unused) |
| `resultapp_branchsubject` | Application | 27 | NEP 2020 curriculum mapping (Branch + Subject + Semester) |
| `resultapp_class` | Application | 8 | Classes (contains 5 legacy/duplicate rows; see Part A) |
| `resultapp_exam` | Application | 3 | Scheduled term-end examinations |
| `resultapp_holiday` | Application | 0 | Holiday exclusions calendar (wired in view/UI; 0 rows saved yet) |
| `resultapp_notice` | Application | 1 | Institutional notices |
| `resultapp_parent` | Application | 3 | Parent accounts linked to User and Student |
| `resultapp_progressreport` | Application | 0 | Qualitative term evaluation reports (active view/UI; unseeded) |
| `resultapp_result` | Application | 1,209 | Subject-wise marks & NEP 2020 components |
| `resultapp_student` | Application | 152 | 150 BSc CS students + 2 legacy test students |
| `resultapp_subject` | Application | 32 | Subject catalog (contains duplicate codes; see Findings) |
| `resultapp_subjectcombination` | Application | 28 | Class-to-Subject assignment mapping |
| `resultapp_teacher` | Application | 1 | Teacher profile with assigned classes/subjects |
| `resultapp_teacher_assigned_classes` | Through-table | 1 | M2M through-table for `Teacher.assigned_classes` |
| `resultapp_teacher_assigned_subjects` | Through-table | 1 | M2M through-table for `Teacher.assigned_subjects` |
| `resultapp_whatsapplog` | Application | 0 | WhatsApp Cloud API webhook/delivery log |
| `auth_user` | Django Auth | 7 | 1 superuser, 1 teacher, 3 parents, 2 students |
| `auth_permission` | Django Auth | 100 | Default Django model permissions |
| `auth_group` | Django Auth | 0 | Unused (SRMS uses custom role-based auth) |
| `auth_group_permissions` | Django Auth | 0 | Unused |
| `auth_user_groups` | Django Auth | 0 | Unused |
| `auth_user_user_permissions` | Django Auth | 0 | Unused |
| `authtoken_token` | DRF Auth | 0 | REST Framework Token auth (endpoint exists) |
| `django_admin_log` | Django Admin | 0 | Standard admin actions log |
| `django_content_type` | Django Core | 25 | Model content types |
| `django_migrations` | Django Core | 36 | 14 resultapp migrations + 22 core migrations |
| `django_session` | Django Core | 61 | Active user login sessions |
| `sqlite_sequence` | SQLite Internal | 23 | Autoincrement trackers |

---

## 2. Systematic Reference Table for all `resultapp_*` Tables

| Table Name | Purpose (One Line) | Row Count | Primary Key | Foreign Keys (Target) | Unique / Index Constraints | Concerns Found |
|:---|:---|:---:|:---|:---|:---|:---|
| `resultapp_adminprofile` | Admin user extended profile and photo | 1 | `id` (INTEGER) | `user_id` &rarr; `auth_user.id` | UNIQUE(`user_id`) | None. Clean 1-to-1 extension. |
| `resultapp_attendance` | Daily & bulk attendance tracking | 88 | `id` (INTEGER) | `student_id` &rarr; `resultapp_student.id`<br>`subject_id` &rarr; `resultapp_subject.id` | UNIQUE(`student_id`, `date`, `subject_id`) | Missing `db_index` on `date` column. |
| `resultapp_auditlog` | Signals-driven audit log for Student & Result CRUD | 1,354 | `id` (INTEGER) | `actor_id` &rarr; `auth_user.id` | None. Ordering is `-timestamp` without index. | Missing `db_index` on `timestamp` and `target_model`. Rapid growth. |
| `resultapp_branch` | Academic degree programmes (NEP 2020) | 2 | `id` (INTEGER) | None | UNIQUE(`branch_code`) | Branch 9 (`CS101`) has 0 classes and 0 subjects attached. |
| `resultapp_branchsubject` | Curriculum mapping: branch + subject + semester | 27 | `id` (INTEGER) | `branch_id` &rarr; `resultapp_branch.id`<br>`subject_id` &rarr; `resultapp_subject.id` | UNIQUE(`branch_id`, `subject_id`, `semester`) | Overlaps logically with `SubjectCombination`. |
| `resultapp_class` | Academic year sections | 8 | `id` (INTEGER) | `branch_id` &rarr; `resultapp_branch.id` | Index on `branch_id` | Contains duplicate/stale rows (IDs 1, 9, 10, 11, 12). No unique constraint on `(class_name, section)`. |
| `resultapp_exam` | Scheduled exams per class and subject | 3 | `id` (INTEGER) | `class_id` &rarr; `resultapp_class.id`<br>`subject_id` &rarr; `resultapp_subject.id` | Index on `exam_date`, `class_id`, `subject_id` | All 3 current rows point to stale Class ID 1. |
| `resultapp_holiday` | Excluded dates for attendance calculations | 0 | `id` (INTEGER) | None | UNIQUE(`date`) | Table is empty because no custom holiday was saved yet. Save path works. |
| `resultapp_notice` | Institutional noticeboard announcements | 1 | `id` (INTEGER) | None | None | None. |
| `resultapp_parent` | Parent portal user profiles | 3 | `id` (INTEGER) | `user_id` &rarr; `auth_user.id`<br>`student_id` &rarr; `resultapp_student.id` | UNIQUE(`user_id`), Index on `student_id` | Only 3 parents exist for 152 students (149 missing parent accounts). |
| `resultapp_progressreport` | Term-end qualitative evaluation & remarks | 0 | `id` (INTEGER) | `student_id` &rarr; `resultapp_student.id` | Index on `student_id` | 0 rows seeded, but active in Parent Portal and AI Chatbot. |
| `resultapp_result` | Subject marks, NEP components & SGPA source | 1,209 | `id` (INTEGER) | `student_id` &rarr; `resultapp_student.id`<br>`class_id` &rarr; `resultapp_class.id`<br>`subject_id` &rarr; `resultapp_subject.id` | Index on `semester`, `student_id`, `class_id`, `subject_id` | Student 1 has 3 duplicate rows for Subject 1, Sem 1. No `unique_together` constraint. |
| `resultapp_student` | Student master roster & demographic data | 152 | `id` (INTEGER) | `student_class_id` &rarr; `resultapp_class.id`<br>`user_id` &rarr; `auth_user.id` | UNIQUE(`roll_id`), UNIQUE(`email`), UNIQUE(`user_id`), Index on `status`, `student_class_id` | 2 students belong to legacy classes (Student 1 &rarr; Class 1, Student 2 &rarr; Class 9). |
| `resultapp_subject` | Master catalog of subjects & credit values | 32 | `id` (INTEGER) | None | None | Duplicate `subject_code` values exist (`USCS203`, `CHEM101`). Cannot add `unique=True` until resolved. |
| `resultapp_subjectcombination` | Section-level subject assignments | 28 | `id` (INTEGER) | `student_class_id` &rarr; `resultapp_class.id`<br>`subject_id` &rarr; `resultapp_subject.id` | Index on `student_class_id`, `subject_id` | No unique constraint on `(student_class, subject)`. Duplicate architecture with `BranchSubject`. |
| `resultapp_teacher` | Teacher profiles with portal access | 1 | `id` (INTEGER) | `user_id` &rarr; `auth_user.id` | UNIQUE(`user_id`) | Clean. |
| `resultapp_teacher_assigned_classes` | Teacher-to-Class RBAC assignment | 1 | `id` (INTEGER) | `teacher_id` &rarr; `resultapp_teacher.id`<br>`class_id` &rarr; `resultapp_class.id` | UNIQUE(`teacher_id`, `class_id`) | Currently points to Class ID 1. |
| `resultapp_teacher_assigned_subjects` | Teacher-to-Subject RBAC assignment | 1 | `id` (INTEGER) | `teacher_id` &rarr; `resultapp_teacher.id`<br>`subject_id` &rarr; `resultapp_subject.id` | UNIQUE(`teacher_id`, `subject_id`) | Clean. |
| `resultapp_whatsapplog` | WhatsApp message delivery audit trail | 0 | `id` (INTEGER) | None | None | Fully wired into `whatsapp.py`, but credentials not configured in local environment. |

---

## 3. Investigation Items Detailed Findings

### Item 1: Empty Tables (0 Rows)
1. **`resultapp_holiday`**:
   - **Status:** **Active & Functional (Not Dead).**
   - **Investigation:** In `views/students.py` (`add_attendance` and `get_holidays`), the holiday save path receives `new_holidays` JSON and calls `Holiday.objects.get_or_create(date=h_dt, defaults={'name': h_name})`. In `test_features.py`, `test_bulk_attendance_with_custom_exclusions_and_db_save` validates that this table persists and calculates exclusions correctly. It has 0 rows in the dev database simply because no user had previously checked "Save to Holiday database model" during manual attendance entry.
2. **`resultapp_whatsapplog`**:
   - **Status:** **Fully Implemented Feature (Inactive locally due to API keys).**
   - **Investigation:** `resultapp/whatsapp.py` contains 5 distinct trigger points calling `WhatsAppLog.objects.create(...)` whenever notifications are dispatched for student results or institutional notices. The table is empty because `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` are not populated in the local `.env`, causing the handler to gracefully fall back without sending live external API requests.
3. **`resultapp_progressreport`**:
   - **Status:** **Not Dead — Active in Parent Portal & AI Chatbot, but completely unseeded.**
   - **Investigation:**
     - Admin entry view: `add_progress_report` in `views/students.py`.
     - Parent views: `parent_dashboard` (`latest_progress`) and `parent_view_progress` in `views/parent.py`.
     - Chatbot: `chatbot_api` in `views/chatbot.py` reads `ProgressReport` to answer qualitative parent inquiries ("How is my child performing?").
     - **Distinction from `Result`:** `Result` stores quantitative per-subject marks (Theory /30, Internal /20, SGPA, grades). `ProgressReport` stores holistic qualitative feedback (`strengths`, `areas_of_improvement`, `teacher_remarks`, `term`). It is NOT redundant with the consolidated marksheet; it represents qualitative report cards.
     - **Recommendation:** Do NOT deprecate. Retain and seed 1 progress report per student in Part B.
4. **`auth_group`, `auth_group_permissions`, `auth_user_groups`, `auth_user_user_permissions`, `authtoken_token`, `django_admin_log`**:
   - **Status:** **Standard Django Framework tables.**
   - **Investigation:** SRMS implements role-based access control via custom role decorators (`@role_required('admin')`, `@role_required('teacher')`, `@role_required('parent')`) and explicit model profiles (`Parent`, `Teacher`, `Student.user`) rather than Django Group memberships. `authtoken_token` belongs to `rest_framework.authtoken` (which has active view `api_token`). These empty tables are standard and harmless.

---

### Item 2: Redundant / Overlapping Tables

1. **`Subject` vs `BranchSubject` vs `SubjectCombination`**:
   - **`resultapp_subject` (32 rows):** Master catalog of subjects. Holds global attributes: `subject_name`, `subject_code`, and NEP credit value `credits`.
   - **`resultapp_branchsubject` (27 rows):** Programme curriculum mapping introduced under NEP 2020. Maps `Branch` (e.g. `BSCCS`) &rarr; `Subject` &rarr; `semester` (1–6). This reflects University of Mumbai's NEP structure where all classes in Year 2 (Semesters 3 & 4) share the same syllabus.
   - **`resultapp_subjectcombination` (28 rows):** Legacy section-level mapping. Maps a specific `Class` instance (e.g. `Class 10 - Section A` or `First Year B.Sc. CS - Section A`) &rarr; `Subject`.
   - **Overlap Analysis:** For NEP 2020 programmes, `SubjectCombination` duplicates what `BranchSubject` already provides. However, `SubjectCombination` is still used for non-branch/legacy classes (Class 10) and backward compatibility in older views.
   - **Recommendation:** Keep both for now to prevent breaking legacy view dependencies; in Part A/B, ensure every class's subjects are properly synchronized between both tables.

2. **Teacher Assignment Through-Tables**:
   - `resultapp_teacher_assigned_classes` (1 row) & `resultapp_teacher_assigned_subjects` (1 row) are standard Django ManyToMany through-tables generated for `Teacher.assigned_classes` and `Teacher.assigned_subjects`.
   - They enforce strict scoping in the teacher portal (`@teacher_required` decorator checks `teacher.assigned_classes.all()` and `teacher.assigned_subjects.all()`). They are not redundant with `Teacher.department`.

---

### Item 3: `resultapp_auditlog` (1,354 Rows)

- **Trigger Mechanism:** Triggered automatically via Django `post_save` and `post_delete` signals in `resultapp/signals.py` on the `Student` and `Result` models.
- **Growth Analysis:**
  - 1,203 rows are `CREATE Result` actions.
  - 151 rows are `CREATE Student` actions.
  - When `scripts/seed_bulk_cs_students.py` created 150 students and 1,200 results, signals fired 1,350 times!
- **Estimated Growth Rate:** In a production setting with 1,000 students and 8 subjects across exams, each examination cycle generates ~8,000 log records.
- **Missing Index:** `AuditLog.Meta` specifies `ordering = ['-timestamp']`, but `timestamp` has NO database index! Filtering by actor or date in the admin console performs a full table scan.
- **Archival / Retention Recommendation:**
  1. Add `db_index=True` to `timestamp` and `target_model`.
  2. Implement an archival management command (e.g., `prune_audit_logs --days=180`) to export or purge records older than 6 months.

---

### Item 4: Row-Count Sanity Checks

1. **Student (152) vs Result (1,209) Ratio:**
   - **Class 13 (First Year B.Sc. CS):** 50 students × 8 subjects (4 in Sem 1 + 4 in Sem 2) = **400 results**.
   - **Class 14 (Second Year B.Sc. CS):** 50 students × 8 subjects (4 in Sem 3 + 4 in Sem 4) = **400 results**.
   - **Class 15 (Third Year B.Sc. CS):** 50 students × 8 subjects (4 in Sem 5 + 4 in Sem 6) = **400 results**.
   - **Class 1 (First Year CS):** 1 student (Shubham) × 6 subjects = **6 results**.
   - **Class 9 (Class 10):** 1 student (Rahul Sharma) × 3 subjects = **3 results**.
   - **Total:** 400 + 400 + 400 + 6 + 3 = **1,209 results**. The ratio is 100% mathematically exact.
2. **Corrupted / Zero Marks Check:**
   - Query: `Result.objects.filter(theory_marks=0, internal_marks=0).count()` &rarr; **0**.
   - Query: `Result.objects.filter(theory_marks__isnull=True).count()` &rarr; **0**.
   - No zeroed or corrupted marks rows exist in the database.
3. **Attendance (88 Rows for 152 Students):**
   - Distinct students in Attendance: **1 student** (Student 1: Shubham).
   - Distinct dates in Attendance: **71 dates**.
   - All 88 attendance rows belong exclusively to Student 1 recorded during early manual testing. No attendance was ever bulk-seeded for the 150 BSc CS students. This confirms it is pre-seed test data, not a persistence bug.

---

## 4. Foreign Key Integrity & Orphaned Records

A complete audit of all 15 foreign key relationships in SQLite produced **0 orphaned foreign keys**:

| Relationship | Orphaned Count | Status |
|:---|:---:|:---|
| `Result` &rarr; `Student` | 0 | OK |
| `Result` &rarr; `Subject` | 0 | OK |
| `Result` &rarr; `Class` | 0 | OK |
| `Student` &rarr; `Class` | 0 | OK |
| `Student` &rarr; `User` | 0 | OK |
| `Attendance` &rarr; `Student` | 0 | OK |
| `Attendance` &rarr; `Subject` | 0 | OK |
| `Parent` &rarr; `Student` | 0 | OK |
| `Parent` &rarr; `User` | 0 | OK |
| `BranchSubject` &rarr; `Branch` | 0 | OK |
| `BranchSubject` &rarr; `Subject` | 0 | OK |
| `SubjectCombination` &rarr; `Class` | 0 | OK |
| `SubjectCombination` &rarr; `Subject` | 0 | OK |
| `Exam` &rarr; `Class` | 0 | OK |
| `Exam` &rarr; `Subject` | 0 | OK |

*Note on SQLite FK Enforcement:* `PRAGMA foreign_keys` currently evaluates to `0` (off) in the SQLite session. Django ORM enforces relationship integrity at the application layer during model operations.

---

## 5. Severity-Ranked Findings List

### High Severity (Data Integrity & Schema Anomalies)
1. **Duplicate / Stale Class Rows in `resultapp_class`:**
   - Class 1 ("First Year CS") and Class 13 ("First Year B.Sc. Computer Science") are duplicate definitions of the same class (both `class_numeric=1`, section `A`, branch `BSCCS`). Class 1 has 1 student (Shubham), 6 results, 3 exams, and 1 teacher assignment. Class 13 has 50 students and 400 results.
   - Classes 9, 10, 11, 12 ("Class 10", "Class 12", "Class 9" ×2) are obsolete test entries. Class 9 has 1 student (Rahul Sharma) and 3 results. Classes 10, 11, 12 have 0 students and 0 results.
2. **Duplicate Subject Codes in `resultapp_subject`:**
   - Code `USCS203` is assigned to ID 2 ("PYTHON") AND ID 3 ("Object Oriented Programming Language").
   - Code `CHEM101` is duplicated across ID 15 ("Chemistry") AND ID 16 ("Chemistry").
   - **Impact:** `Subject.subject_code` cannot have `unique=True` applied until these duplicates are deduplicated.
3. **Duplicate Result Entry for Student 1:**
   - Student 1 has 3 separate rows in `resultapp_result` for Subject 1, Semester 1 (Result IDs 1, 4, and 5).
   - **Impact:** Adding a database constraint `UNIQUE(student, subject, semester)` will fail until these test duplicates are consolidated.

### Medium Severity (Performance & Indexing)
4. **Missing Index on `Attendance.date`:**
   - The bulk attendance query and monthly reports filter heavily by `date__gte`, `date__lte`, and `date__in`. Currently unindexed.
5. **Missing Indexes on `AuditLog` (`timestamp`, `target_model`):**
   - `AuditLog` has 1,354+ rows and default ordering `-timestamp`, but lacks an index on `timestamp`.

### Low Severity (Schema Redundancy & Conventions)
6. **Unused Branch ID 9 (`CS101`):**
   - Branch ID 9 (`branch_code="CS101", branch_name="Computer Science"`) has 0 classes and 0 subjects attached.
7. **Subject Mapping Architecture Dual-Maintenance:**
   - `BranchSubject` and `SubjectCombination` both map curriculum relationships, requiring synchronization in admin views.

---

## 6. Action Plan: "Safe to Fix Now" vs "Needs Decision First"

### A. Safe to Fix Now (Implemented in Django Migration 0015)
1. **Add `db_index=True` to `Attendance.date`** &rarr; Optimizes date range queries across thousands of records.
2. **Add `db_index=True` to `AuditLog.timestamp`** &rarr; Optimizes reverse chronological log retrieval.
3. **Add `db_index=True` to `AuditLog.target_model`** &rarr; Optimizes model-specific audit history lookups.

### B. Needs Decision First (Requires User Confirmation)
1. **Class Cleanup (Part A):**
   - Merging Class 1 into Class 13 (reassigning Student 1, his 6 results, 3 exams, and 1 teacher assignment to Class 13).
   - Deleting obsolete Classes 9, 10, 11, 12 (and reassigning or removing Student 2 "Rahul Sharma").
2. **Subject Code Deduplication:**
   - Re-keying or removing duplicate subject rows (ID 2 vs ID 3 for `USCS203`, ID 15 vs ID 16 for `CHEM101`) before enforcing `unique=True` on `Subject.subject_code`.
3. **Result Constraint Resolution:**
   - Removing the 2 duplicate test results for Student 1 (IDs 4 and 5) before enforcing `unique_together = ['student', 'subject', 'semester']`.

---
*End of Audit Report.*
