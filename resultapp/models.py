from django.db import models
from django.contrib.auth.models import User


class Branch(models.Model):
    """
    Academic branch / programme, e.g. BSc Computer Science, BSc IT, BCA.
    Introduced so the college can run several NEP 2020 programmes side by
    side (not just BSc CS) from the same admin panel.
    """
    branch_name = models.CharField(max_length=150)
    branch_code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    status = models.IntegerField(default=1)  # 1 = active, 0 = inactive
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ['branch_name']

    def __str__(self):
        return f"{self.branch_name} ({self.branch_code})"


class Class(models.Model):
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='classes',
        help_text="Programme / branch this class belongs to, e.g. BSc Computer Science"
    )
    class_name = models.CharField(max_length=100)
    class_numeric = models.IntegerField()
    section = models.CharField(max_length=10)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Classes"

    def __str__(self):
        if self.branch:
            return f"{self.branch.branch_code} - {self.class_name} - Section {self.section}"
        return f"{self.class_name} - Section {self.section}"


class Subject(models.Model):
    subject_name = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=20)
    # NEP 2020 credit value for this subject (typically 2-4 credits/subject).
    # Used to compute credit-weighted SGPA/CGPA: SGPA = Sum(credit x grade_point) / Sum(credit)
    credits = models.PositiveIntegerField(default=4, help_text="NEP 2020 credit value for this subject (e.g. 2, 3, 4)")
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject_name} - {self.subject_code}"


class BranchSubject(models.Model):
    """
    Curriculum mapping: which subjects belong to a branch, and in which
    semester, under the NEP 2020 credit-based structure.
    """
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 7)]

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='branch_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semester = models.IntegerField(choices=SEMESTER_CHOICES, default=1)
    status = models.IntegerField(default=1)  # 1 = active, 0 = inactive
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Branch Subjects"
        unique_together = ['branch', 'subject', 'semester']
        ordering = ['branch', 'semester', 'subject']

    def __str__(self):
        return f"{self.branch.branch_code} - Sem {self.semester} - {self.subject.subject_name}"


class Student(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    roll_id = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=50, unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    dob = models.DateField(null=True, blank=True)
    student_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True)
    reg_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    status = models.IntegerField(default=1, db_index=True)
    photo = models.ImageField(upload_to='student_faces/', null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    # Optional direct login account for the student (mirrors Parent.user).
    # Linked automatically the first time this student's on-file email
    # signs in with Google — no separate account creation step needed.
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='student_account'
    )

    def __str__(self):
        return self.name

    def get_consolidated_marksheet(self, semester=None):
        """
        Aggregates all subjects for a student for the given semester into a
        consolidated marksheet view according to NEP 2020 guidelines.
        Subject credits are pulled directly from Subject (with default 4 only if null/missing).
        """
        from resultapp.views.students import get_sgpa

        results_qs = self.result_set.select_related('subject', 'student_class').order_by('subject__subject_name')
        available_semesters = list(
            self.result_set.values_list('semester', flat=True).distinct().order_by('semester')
        )

        if semester is None:
            if available_semesters:
                semester = available_semesters[-1]
            else:
                semester = 1
        else:
            try:
                semester = int(semester)
            except (ValueError, TypeError):
                semester = 1

        semester_results = [r for r in results_qs if r.semester == semester]

        subject_rows = []
        total_credits = 0
        total_obtained = 0
        total_max = 0

        for r in semester_results:
            # Explicit real credits check: only fallback to 4 if subject has no credits or null
            subj_credits = r.subject.credits if (r.subject and r.subject.credits is not None) else 4
            total_credits += subj_credits
            total_obtained += r.total_obtained
            total_max += r.total_max

            subject_rows.append({
                'result_id': r.id,
                'subject_name': r.subject.subject_name if r.subject else 'Unknown',
                'subject_code': r.subject.subject_code if r.subject else '',
                'credits': subj_credits,
                'theory_marks': r.theory_marks,
                'internal_marks': r.internal_marks,
                'practical_marks': r.practical_marks,
                'oral_marks': r.oral_marks,
                'total_obtained': r.total_obtained,
                'total_max': r.total_max,
                'percentage': r.subject_percentage,
                'nep_grade': r.nep_grade,
                'nep_grade_point': r.nep_grade_point,
                'is_pass': r.is_subject_pass,
            })

        overall_percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0
        is_pass = (len(semester_results) > 0) and all(r.is_subject_pass for r in semester_results)
        sgpa = get_sgpa(semester_results) if semester_results else 0.0

        return {
            'student': self,
            'semester': semester,
            'available_semesters': available_semesters,
            'subjects': subject_rows,
            'results': semester_results,
            'total_credits': total_credits,
            'total_obtained': total_obtained,
            'total_max': total_max,
            'overall_percentage': overall_percentage,
            'sgpa': sgpa,
            'is_pass': is_pass,
            'status': 'PASS' if is_pass else 'FAIL',
        }


class SubjectCombination(models.Model):
    student_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student_class} - {self.subject}"


class Result(models.Model):
    """
    Mumbai University NEP 2020 marks structure (per subject) — used for
    BSc Computer Science and other NEP-2020-aligned branches:
      Theory (Semester End Exam) : max 30  — pass >= 12 (40%)
      Internal Assessment        : max 20  — pass >=  8 (40%)
      Practical / Term Work      : max 25  — pass >= 10 (40%)  [optional]
      Oral / Viva                : max 25  — pass >= 10 (40%)  [optional]
      Total                      : 100 (theory+internal) or up to 100 with prac/oral

    SGPA/CGPA are computed as NEP 2020 credit-weighted averages using each
    Subject's `credits` value:
      SGPA = Σ(credit × grade_point) / Σ(credit)
    See `get_sgpa()` in views.py.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    student_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    semester = models.IntegerField(default=1, db_index=True)

    # NEP 2020 component marks
    theory_marks     = models.IntegerField(default=0)   # out of 30
    internal_marks   = models.IntegerField(default=0)   # out of 20
    practical_marks  = models.IntegerField(null=True, blank=True)  # out of 25 (optional)
    oral_marks       = models.IntegerField(null=True, blank=True)  # out of 25 (optional)

    # Legacy field — kept for backward compatibility, auto-computed on save
    marks = models.IntegerField(default=0)

    posting_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Keep legacy marks = total obtained
        self.marks = self.total_obtained
        super().save(*args, **kwargs)

    @property
    def total_obtained(self):
        t = (self.theory_marks or 0) + (self.internal_marks or 0)
        if self.practical_marks is not None:
            t += self.practical_marks
        if self.oral_marks is not None:
            t += self.oral_marks
        return t

    @property
    def total_max(self):
        base = 50  # theory(30) + internal(20)
        if self.practical_marks is not None:
            base += 25
        if self.oral_marks is not None:
            base += 25
        return base

    @property
    def subject_percentage(self):
        if self.total_max == 0:
            return 0
        return round((self.total_obtained / self.total_max) * 100, 2)

    @property
    def is_subject_pass(self):
        """NEP 2020: must pass each component separately at 40%"""
        if self.theory_marks < 12:       # 40% of 30
            return False
        if self.internal_marks < 8:      # 40% of 20
            return False
        if self.practical_marks is not None and self.practical_marks < 10:  # 40% of 25
            return False
        if self.oral_marks is not None and self.oral_marks < 10:            # 40% of 25
            return False
        return True

    @property
    def nep_grade(self):
        if not self.is_subject_pass:
            return 'F'
        p = self.subject_percentage
        if p >= 80:   return 'O'
        if p >= 70:   return 'A+'
        if p >= 60:   return 'A'
        if p >= 55:   return 'B+'
        if p >= 50:   return 'B'
        if p >= 45:   return 'C'
        if p >= 40:   return 'D'
        return 'F'

    @property
    def nep_grade_point(self):
        grade_points = {'O': 10, 'A+': 9, 'A': 8, 'B+': 7, 'B': 6, 'C': 5, 'D': 4, 'F': 0}
        return grade_points.get(self.nep_grade, 0)

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.total_obtained}/{self.total_max}"


class Notice(models.Model):
    title = models.CharField(max_length=255)
    detail = models.TextField()
    posting_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Holiday(models.Model):
    name = models.CharField(max_length=150)
    date = models.DateField(unique=True)

    def __str__(self):
        return f"{self.name} ({self.date})"


class Parent(models.Model):
    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parents')
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES, blank=True, null=True)
    email_alerts = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - Parent of {self.student.name}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 7)]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(
        'Subject', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attendance_records',
        help_text="Subject for which attendance is being marked (optional, for subject-wise attendance)"
    )
    semester = models.IntegerField(
        choices=SEMESTER_CHOICES, null=True, blank=True,
        help_text="Semester number (1–6), used for subject-wise bulk attendance"
    )
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Allow same student on same date for different subjects
        unique_together = ['student', 'date', 'subject']
        ordering = ['-date']

    def __str__(self):
        sub = f" ({self.subject.subject_name})" if self.subject else ""
        return f"{self.student.name} - {self.date}{sub} - {self.status}"


class ProgressReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.CharField(max_length=50, default='')
    overall_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    grade = models.CharField(max_length=10, default='N/A')
    teacher_remarks = models.TextField(default='')
    strengths = models.TextField(blank=True, null=True)
    areas_of_improvement = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.name} - {self.term}"


class Teacher(models.Model):
    """
    Teacher account — created by admin.  Linked to a Django User via
    OneToOne.  Access is scoped to assigned_classes and assigned_subjects;
    the teacher portal enforces this at the view level via the
    teacher_required decorator in views.py.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='teacher_account'
    )
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=150, blank=True, null=True)
    assigned_classes = models.ManyToManyField(
        Class, blank=True, related_name='teachers',
        help_text='Classes this teacher is allowed to view/manage'
    )
    assigned_subjects = models.ManyToManyField(
        Subject, blank=True, related_name='teachers',
        help_text='Subjects this teacher is responsible for'
    )
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Teacher)"


class AdminProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='admin_profile'
    )
    photo = models.ImageField(upload_to='admin_photos/', null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin Profile for {self.user.username}"


class Exam(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    student_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exams')
    exam_date = models.DateField(db_index=True)
    title = models.CharField(max_length=200, help_text="e.g. Term End Semester Exam")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject.subject_name} ({self.student_class})"


class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20) # CREATE, UPDATE, DELETE
    target_model = models.CharField(max_length=100, db_index=True) # Student, Result
    target_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.actor} - {self.action} {self.target_model} ({self.target_id}) at {self.timestamp}"


class WhatsAppLog(models.Model):
    recipient_number = models.CharField(max_length=30)
    message_type = models.CharField(max_length=20) # notice, result
    status = models.CharField(max_length=20) # sent, failed
    response_payload = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.message_type} to {self.recipient_number} ({self.status}) at {self.timestamp}"
