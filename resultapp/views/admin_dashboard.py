import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Q, Count
from django.db import IntegrityError
from django.core.mail import send_mail

from resultapp.models import (
    Branch, Subject, BranchSubject, Class, SubjectCombination, Notice,
    Student, Result, Attendance, AdminProfile, Parent
)
from .students import paginate, get_grade, get_sgpa
from .decorators import role_required

logger = logging.getLogger(__name__)


def index(request):
    notices = Notice.objects.all().order_by('-id')
    total_students = Student.objects.count()
    total_subjects = Subject.objects.count()
    total_classes = Class.objects.count()
    total_results = Result.objects.values('student').distinct().count()
    return render(request, 'index.html', {
        'notices': notices,
        'total_students': total_students,
        'total_subjects': total_subjects,
        'total_classes': total_classes,
        'total_results': total_results,
    })


def notice_detail(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    return render(request, 'notice_detail.html', {'notice': notice})


@role_required('admin')
def admin_dashboard(request):
    total_students = Student.objects.count()
    total_subjects = Subject.objects.count()
    total_classes = Class.objects.count()
    total_results = Result.objects.values('student').distinct().count()
    return render(request, 'admin_dashboard.html', {
        'total_students': total_students,
        'total_subjects': total_subjects,
        'total_classes': total_classes,
        'total_results': total_results,
    })


@role_required('admin')
def create_branch(request):
    if request.method == 'POST':
        try:
            branch_name = request.POST.get('branchname')
            branch_code = request.POST.get('branchcode')
            description = request.POST.get('description', '')
            Branch.objects.create(
                branch_name=branch_name,
                branch_code=branch_code.upper() if branch_code else branch_code,
                description=description,
            )
            messages.success(request, "Branch created successfully!")
        except IntegrityError:
            messages.error(request, f"A branch with the code \"{branch_code}\" already exists. Please use a different branch code.")
        except Exception:
            logger.exception("Failed to create branch")
            messages.error(request, "Couldn't create the branch. An unexpected error occurred.")
        return redirect('create_branch')
    return render(request, 'create_branch.html')


@role_required('admin')
def manage_branches(request):
    if request.method == 'POST' and request.POST.get('delete'):
        try:
            branch_obj = get_object_or_404(Branch, id=request.POST.get('delete'))
            branch_obj.delete()
            messages.success(request, "Branch deleted successfully!")
        except Exception:
            logger.exception("Failed to delete branch")
            messages.error(request, "Couldn't delete the branch. An unexpected error occurred.")
        return redirect('manage_branches')

    branches = Branch.objects.all().order_by('branch_name')
    q = request.GET.get('q', '').strip()
    if q:
        branches = branches.filter(Q(branch_name__icontains=q) | Q(branch_code__icontains=q) | Q(description__icontains=q))
    page_obj = paginate(request, branches)
    return render(request, 'manage_branches.html', {'branches': page_obj, 'page_obj': page_obj, 'q': q})


@role_required('admin')
def edit_branch(request, branch_id):
    branch_obj = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        try:
            branch_obj.branch_name = request.POST.get('branchname')
            branch_code = request.POST.get('branchcode')
            branch_obj.branch_code = branch_code.upper() if branch_code else branch_code
            branch_obj.description = request.POST.get('description', '')
            branch_obj.save()
            messages.success(request, "Branch updated successfully!")
            return redirect('manage_branches')
        except IntegrityError:
            messages.error(request, f"A branch with the code \"{branch_code}\" already exists. Please use a different branch code.")
        except Exception:
            logger.exception("Failed to edit branch %s", branch_id)
            messages.error(request, "Couldn't update the branch. An unexpected error occurred.")
    return render(request, 'edit_branch.html', {'branch_obj': branch_obj})


@role_required('admin')
def add_branch_subject(request):
    branches = Branch.objects.all()
    subjects = Subject.objects.all()
    if request.method == 'POST':
        try:
            branch_id = request.POST.get('branch')
            subject_id = request.POST.get('subject')
            semester = request.POST.get('semester')
            BranchSubject.objects.create(
                branch_id=branch_id, subject_id=subject_id,
                semester=semester, status=1,
            )
            messages.success(request, "Subject added to branch successfully!")
        except IntegrityError:
            messages.error(request, "This subject is already assigned to that branch and semester.")
        except Exception:
            logger.exception("Failed to assign subject to branch")
            messages.error(request, "Couldn't add the subject to the branch. An unexpected error occurred.")
        return redirect('add_branch_subject')
    return render(request, 'add_branch_subject.html', {'branches': branches, 'subjects': subjects})


@role_required('admin')
def manage_branch_subjects(request):
    aid = request.POST.get('aid') or request.GET.get('aid')
    did = request.POST.get('did') or request.GET.get('did')
    rid = request.POST.get('remove') or request.GET.get('remove')
    if aid or did or rid:
        try:
            if aid:
                BranchSubject.objects.filter(id=aid).update(status=1)
                messages.success(request, "Branch subject activated successfully!")
            elif did:
                BranchSubject.objects.filter(id=did).update(status=0)
                messages.success(request, "Branch subject deactivated successfully!")
            elif rid:
                BranchSubject.objects.filter(id=rid).delete()
                messages.success(request, "Branch subject removed successfully!")
        except Exception:
            logger.exception("Failed to update branch subject")
            messages.error(request, "Couldn't update the branch subject. An unexpected error occurred.")
        return redirect('manage_branch_subjects')

    branch_subjects = BranchSubject.objects.select_related('branch', 'subject').all().order_by('branch__branch_name', 'semester')
    page_obj = paginate(request, branch_subjects)
    return render(request, 'manage_branch_subjects.html', {'branch_subjects': page_obj, 'page_obj': page_obj})


@role_required('admin')
def create_class(request):
    branches = Branch.objects.all()
    if request.method == 'POST':
        try:
            branch_id = request.POST.get('branch') or None
            class_name = request.POST.get('classname')
            class_numeric = request.POST.get('classnamenumeric')
            section = request.POST.get('section')
            Class.objects.create(
                branch_id=branch_id, class_name=class_name,
                class_numeric=class_numeric, section=section,
            )
            messages.success(request, "Class created successfully!")
        except ValueError:
            messages.error(request, "Class number must be a whole number (e.g. 1, 2, 3).")
        except Exception:
            logger.exception("Failed to create class")
            messages.error(request, "Couldn't create the class. An unexpected error occurred.")
        return redirect('create_class')
    return render(request, 'create_class.html', {'branches': branches})


@role_required('admin')
def manage_classes(request):
    if request.method == 'POST' and request.POST.get('delete'):
        try:
            class_obj = get_object_or_404(Class, id=request.POST.get('delete'))
            class_obj.delete()
            messages.success(request, "Class deleted successfully!")
        except Exception:
            logger.exception("Failed to delete class")
            messages.error(request, "Couldn't delete the class. An unexpected error occurred.")
        return redirect('manage_classes')

    classes = Class.objects.select_related('branch').all().order_by('branch__branch_name', 'class_name', 'section')
    q = request.GET.get('q', '').strip()
    if q:
        classes = classes.filter(
            Q(class_name__icontains=q) | Q(section__icontains=q) |
            Q(branch__branch_name__icontains=q) | Q(branch__branch_code__icontains=q)
        )
    page_obj = paginate(request, classes)
    return render(request, 'manage_classes.html', {'classes': page_obj, 'page_obj': page_obj, 'q': q})


@role_required('admin')
def edit_class(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    branches = Branch.objects.all()
    if request.method == 'POST':
        try:
            class_obj.branch_id = request.POST.get('branch') or None
            class_obj.class_name = request.POST.get('classname')
            class_obj.class_numeric = request.POST.get('classnamenumeric')
            class_obj.section = request.POST.get('section')
            class_obj.save()
            messages.success(request, "Class updated successfully!")
            return redirect('manage_classes')
        except ValueError:
            messages.error(request, "Class number must be a whole number (e.g. 1, 2, 3).")
        except Exception:
            logger.exception("Failed to edit class %s", class_id)
            messages.error(request, "Couldn't update the class. An unexpected error occurred.")
    return render(request, 'edit_class.html', {'class_obj': class_obj, 'branches': branches})


@role_required('admin')
def create_subject(request):
    branches = Branch.objects.filter(status=1)
    semester_choices = [(i, f"Semester {i}") for i in range(1, 7)]

    if request.method == 'POST':
        try:
            subject_obj = Subject.objects.create(
                subject_name=request.POST.get('subjectname'),
                subject_code=request.POST.get('subjectcode'),
                credits=request.POST.get('credits') or 4,
            )

            branch_id = request.POST.get('branch') or None
            semester  = request.POST.get('semester') or None
            if branch_id and semester:
                branch = Branch.objects.get(id=branch_id)
                BranchSubject.objects.get_or_create(
                    branch=branch,
                    subject=subject_obj,
                    semester=int(semester),
                )
                messages.success(
                    request,
                    f"Subject '{subject_obj.subject_name}' created and assigned to "
                    f"{branch.branch_name} — Semester {semester}!"
                )
            else:
                messages.success(request, f"Subject '{subject_obj.subject_name}' created successfully!")

        except ValueError:
            messages.error(request, "Credits must be a positive whole number (e.g. 2, 3, 4).")
        except Exception:
            logger.exception("Failed to create subject")
            messages.error(request, "Couldn't create the subject. An unexpected error occurred.")
        return redirect('create_subject')

    return render(request, 'create_subject.html', {
        'branches': branches,
        'semester_choices': semester_choices,
    })


@role_required('admin')
def manage_subject(request):
    if request.method == 'POST' and request.POST.get('delete'):
        try:
            subject_obj = get_object_or_404(Subject, id=request.POST.get('delete'))
            subject_obj.delete()
            messages.success(request, "Subject deleted successfully!")
        except Exception:
            logger.exception("Failed to delete subject")
            messages.error(request, "Couldn't delete the subject. An unexpected error occurred.")
        return redirect('manage_subject')

    subjects = Subject.objects.all().order_by('subject_name')
    q = request.GET.get('q', '').strip()
    if q:
        subjects = subjects.filter(Q(subject_name__icontains=q) | Q(subject_code__icontains=q))
    page_obj = paginate(request, subjects)
    return render(request, 'manage_subject.html', {'subjects': page_obj, 'page_obj': page_obj, 'q': q})


@role_required('admin')
def edit_subject(request, subject_id):
    subject_obj = get_object_or_404(Subject, id=subject_id)
    if request.method == 'POST':
        try:
            subject_obj.subject_name = request.POST.get('subjectname')
            subject_obj.subject_code = request.POST.get('subjectcode')
            subject_obj.credits = request.POST.get('credits') or 4
            subject_obj.save()
            messages.success(request, "Subject updated successfully!")
            return redirect('manage_subject')
        except ValueError:
            messages.error(request, "Credits must be a positive whole number (e.g. 2, 3, 4).")
        except Exception:
            logger.exception("Failed to edit subject %s", subject_id)
            messages.error(request, "Couldn't update the subject. An unexpected error occurred.")
    return render(request, 'edit_subject.html', {'subject_obj': subject_obj})


@role_required('admin')
def add_subject_combination(request):
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class')
            subject_id = request.POST.get('subject')
            SubjectCombination.objects.create(student_class_id=class_id, subject_id=subject_id, status=1)
            messages.success(request, "Subject combination created successfully!")
        except ValueError:
            messages.error(request, "Please select both a class and a subject.")
        except Exception:
            logger.exception("Failed to create subject combination")
            messages.error(request, "Couldn't create the subject combination. An unexpected error occurred.")
        return redirect('add_subject_combination')
    return render(request, 'add_subject_combination.html', {'classes': classes, 'subjects': subjects})


@role_required('admin')
def manage_subject_combination(request):
    if request.method == 'POST':
        aid = request.POST.get('aid')
        did = request.POST.get('did')
        try:
            if aid:
                SubjectCombination.objects.filter(id=aid).update(status=1)
                messages.success(request, "Subject combination activated successfully!")
            elif did:
                SubjectCombination.objects.filter(id=did).update(status=0)
                messages.success(request, "Subject combination deactivated successfully!")
        except Exception:
            logger.exception("Failed to update subject combination")
            messages.error(request, "Couldn't update the subject combination. An unexpected error occurred.")
        return redirect('manage_subject_combination')

    combinations = SubjectCombination.objects.select_related('student_class', 'subject').all().order_by('student_class__class_name', 'student_class__section', 'subject__subject_name')
    q = request.GET.get('q', '').strip()
    if q:
        combinations = combinations.filter(
            Q(student_class__class_name__icontains=q) | Q(student_class__section__icontains=q) |
            Q(subject__subject_name__icontains=q) | Q(subject__subject_code__icontains=q)
        )
    page_obj = paginate(request, combinations)
    return render(request, 'manage_subject_combination.html', {'combinations': page_obj, 'page_obj': page_obj, 'q': q})


@role_required('admin')
def add_notice(request):
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            details = request.POST.get('details')
            notice = Notice.objects.create(title=title, detail=details)
        except Exception:
            logger.exception("Failed to post notice")
            messages.error(request, "Couldn't post the notice. An unexpected error occurred.")
            return redirect('add_notice')

        try:
            all_student_emails = list(Student.objects.filter(status=1).values_list('email', flat=True))
            all_parent_emails = list(
                Parent.objects.select_related('user').values_list('user__email', flat=True)
            )
            all_emails = list(filter(None, set(all_student_emails + all_parent_emails)))

            if all_emails:
                send_mail(
                    subject=f'New Notice: {title} - SRMS',
                    message=(
                        f'Dear Student/Parent,\n\nA new notice has been posted:\n\n'
                        f'Title: {title}\n\n{details}\n\n'
                        'Please visit the school portal for more details.\n\nRegards,\nSRMS College'
                    ),
                    from_email=None,
                    recipient_list=all_emails,
                    fail_silently=True,
                )

            # Send WhatsApp notifications to parents
            if request.POST.get('send_whatsapp') == '1':
                try:
                    from resultapp.whatsapp import send_whatsapp_message
                    parents_qs = Parent.objects.filter(student__status=1)
                    for parent_obj in parents_qs:
                        if parent_obj.phone:
                            msg_text = f"Notice Alert: {title}\n\n{details[:100]}...\n\nPlease login to parent portal to read full notice."
                            send_whatsapp_message(parent_obj.phone, msg_text, 'notice')
                except Exception:
                    logger.exception("Notice created but WhatsApp notification failed")

            messages.success(request, "Notice added successfully!")
        except Exception:
            logger.exception("Notice created but email/WhatsApp notification failed")
            messages.success(request, "Notice added successfully!")
            messages.warning(request, "Note: some students/parents may not have been notified.")
    return render(request, 'add_notice.html')


@role_required('admin')
def manage_notice(request):
    if request.method == 'POST' and request.POST.get('delete'):
        try:
            notice_obj = get_object_or_404(Notice, id=request.POST.get('delete'))
            notice_obj.delete()
            messages.success(request, "Notice deleted successfully!")
        except Exception:
            logger.exception("Failed to delete notice")
            messages.error(request, "Couldn't delete the notice. An unexpected error occurred.")
        return redirect('manage_notice')

    notices = Notice.objects.all().order_by('-posting_date')
    q = request.GET.get('q', '').strip()
    if q:
        notices = notices.filter(Q(title__icontains=q) | Q(detail__icontains=q))
    page_obj = paginate(request, notices)
    return render(request, 'manage_notice.html', {'notices': page_obj, 'page_obj': page_obj, 'q': q})


@role_required('admin')
def admin_analytics(request):
    """
    Performance optimized and cached admin analytics view.
    Executes exactly 6 database queries regardless of student count,
    caches context for 5 minutes, and supports invalidation on result save.
    """
    from django.core.cache import cache
    import json
    
    # Try fetching from cache
    cache_key = 'admin_analytics_data'
    cached_data = cache.get(cache_key)
    
    if cached_data is not None and isinstance(cached_data, dict):
        return render(request, 'admin_analytics.html', cached_data)

    # Cache miss: compute analytics context
    all_students = list(Student.objects.all().select_related('student_class__branch'))
    total_students = len(all_students)

    # 1. Group results by student in memory
    from collections import defaultdict
    results_qs = list(Result.objects.all().select_related('student', 'student_class', 'subject'))
    student_results = defaultdict(list)
    for r in results_qs:
        student_results[r.student.id].append(r)

    passed = 0
    failed_count = 0
    top_performers = 0
    at_risk_students = 0

    grade_dist = {'O': 0, 'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C+': 0, 'C': 0, 'D': 0, 'F': 0}

    for student in all_students:
        results = student_results[student.id]
        if not results:
            continue
        total_marks = sum(r.total_obtained for r in results)
        max_marks   = sum(r.total_max for r in results)
        pct = (total_marks / max_marks * 100) if max_marks > 0 else 0
        failed_any = any(not r.is_subject_pass for r in results)
        if not failed_any:
            passed += 1
        else:
            failed_count += 1
        if pct >= 90:
            top_performers += 1
        if pct < 40 or failed_any:
            at_risk_students += 1

        # Grade distribution
        g = get_grade(pct, failed_any)
        if g in grade_dist:
            grade_dist[g] += 1

    pass_percentage = round((passed / total_students * 100) if total_students > 0 else 0, 1)

    # 2. Optimized Attendance aggregation (1 query instead of N)
    from datetime import datetime, timedelta
    from .students import compute_attendance_stats
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    attendance_qs = list(Attendance.objects.filter(student__status=1, date__gte=thirty_days_ago))
    student_attendance = defaultdict(lambda: defaultdict(set))
    for record in attendance_qs:
        student_attendance[record.student_id][record.date].add(record.status)

    total_percentage = 0.0
    student_count_with_attendance = 0
    for student in all_students:
        date_statuses = student_attendance[student.id]
        if not date_statuses:
            continue
        total_days = 0
        present_days = 0
        late_days = 0
        absent_days = 0
        excused_days = 0
        for date, statuses in date_statuses.items():
            if 'present' in statuses:
                present_days += 1
                total_days += 1
            elif 'late' in statuses:
                late_days += 1
                total_days += 1
            elif 'absent' in statuses:
                absent_days += 1
                total_days += 1
            elif 'excused' in statuses:
                excused_days += 1
        
        if total_days > 0:
            pct_att = (present_days + late_days) / total_days * 100
            total_percentage += pct_att
            student_count_with_attendance += 1

    avg_attendance = round(total_percentage / student_count_with_attendance, 1) if student_count_with_attendance > 0 else 0.0

    # 3. Class-wise averages optimized (1 query aggregation instead of C)
    classes = list(Class.objects.all())
    class_labels = []
    class_avgs = []
    from django.db.models import Avg
    class_averages = Result.objects.values('student_class_id').annotate(avg_marks=Avg('marks'))
    class_avg_map = {item['student_class_id']: item['avg_marks'] for item in class_averages}
    
    for cls in classes:
        avg = class_avg_map.get(cls.id, 0)
        class_labels.append(str(cls.class_name))
        class_avgs.append(round(avg, 1) if avg else 0)

    # 4. Group students by branch
    branch_students_map = defaultdict(list)
    for student in all_students:
        if student.student_class and student.student_class.branch_id:
            branch_students_map[student.student_class.branch_id].append(student)

    # 5. Branch-wise pass/fail/avg calculation optimized
    branches = list(Branch.objects.all())
    branch_labels = []
    branch_pass_counts = []
    branch_fail_counts = []
    branch_avg_pcts = []
    for branch in branches:
        b_pass = 0
        b_fail = 0
        b_pcts = []
        b_students = branch_students_map[branch.id]
        for s in b_students:
            r_list = student_results[s.id]
            if not r_list:
                continue
            t_obt = sum(r.total_obtained for r in r_list)
            t_max = sum(r.total_max for r in r_list)
            pct_s = (t_obt / t_max * 100) if t_max > 0 else 0
            b_pcts.append(pct_s)
            if any(not r.is_subject_pass for r in r_list):
                b_fail += 1
            else:
                b_pass += 1
        
        branch_labels.append(branch.branch_code)
        branch_pass_counts.append(b_pass)
        branch_fail_counts.append(b_fail)
        branch_avg_pcts.append(round(sum(b_pcts) / len(b_pcts), 1) if b_pcts else 0.0)

    # 6. SGPA buckets optimized
    sgpa_buckets = [0] * 11
    for student in all_students:
        r_list = student_results[student.id]
        if not r_list:
            continue
        sgpa_val = get_sgpa(r_list)
        bucket = min(10, max(0, int(sgpa_val)))
        sgpa_buckets[bucket] += 1
    sgpa_labels = [str(i) for i in range(11)]

    context = {
        'pass_percentage': pass_percentage,
        'avg_attendance': avg_attendance,
        'top_performers': top_performers,
        'at_risk_students': at_risk_students,
        'class_labels_json': json.dumps(class_labels),
        'class_avgs_json': json.dumps(class_avgs),
        'grade_o':     grade_dist.get('O', 0),
        'grade_aplus': grade_dist.get('A+', 0),
        'grade_a':     grade_dist.get('A', 0),
        'grade_bplus': grade_dist.get('B+', 0),
        'grade_b':     grade_dist.get('B', 0),
        'grade_cplus': grade_dist.get('C+', 0),
        'grade_c':     grade_dist.get('C', 0),
        'grade_d':     grade_dist.get('D', 0),
        'grade_f':     grade_dist.get('F', 0),
        'total_students': total_students,
        'passed_count': passed,
        'failed_count': failed_count,
        'branch_labels_json':      json.dumps(branch_labels),
        'branch_pass_json':        json.dumps(branch_pass_counts),
        'branch_fail_json':        json.dumps(branch_fail_counts),
        'branch_avg_pcts_json':    json.dumps(branch_avg_pcts),
        'sgpa_labels_json':        json.dumps(sgpa_labels),
        'sgpa_buckets_json':       json.dumps(sgpa_buckets),
    }

    # Store in cache for 5 minutes (300 seconds)
    cache.set(cache_key, context, timeout=300)

    return render(request, 'admin_analytics.html', context)


@role_required('admin')
def create_admin(request):
    """Allow the current superuser to create additional admin accounts."""
    error = None
    success = None

    if request.method == 'POST':
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name', '').strip()
        username     = request.POST.get('username', '').strip()
        email        = request.POST.get('email', '').strip()
        password     = request.POST.get('password', '').strip()
        confirm_pass = request.POST.get('confirm_password', '').strip()

        if not all([first_name, username, email, password, confirm_pass]):
            error = 'All fields except Last Name are required.'
        elif password != confirm_pass:
            error = 'Passwords do not match.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters long.'
        elif User.objects.filter(username=username).exists():
            error = f'Username "{username}" is already taken.'
        elif User.objects.filter(email=email).exists():
            error = f'An account with email "{email}" already exists.'
        else:
            try:
                new_admin = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                photo = request.FILES.get('photo')
                if photo:
                    AdminProfile.objects.create(user=new_admin, photo=photo)
                try:
                    send_mail(
                        subject='Your SRMS Admin Account Has Been Created',
                        message=(
                            f'Hello {first_name},\n\n'
                            'An admin account has been created for you on the SRMS portal.\n\n'
                            f'Username : {username}\n'
                            f'Email    : {email}\n'
                            f'Login URL: /admin-login/\n\n'
                            'Please log in and change your password immediately.\n\n'
                            'Regards,\nSRMS System'
                        ),
                        from_email=None,
                        recipient_list=[email],
                        fail_silently=True,
                    )
                except Exception:
                    logger.exception("Failed to send welcome email to new admin %s", email)
                messages.success(request, f'Admin account created for {first_name} ({username}).')
                return redirect('create_admin')
            except Exception:
                logger.exception("Failed to create admin account")
                error = 'Could not create admin. An unexpected error occurred.'

    admins = User.objects.filter(is_superuser=True).order_by('date_joined')
    return render(request, 'admin/create_admin.html', {
        'error': error,
        'admins': admins,
    })


@role_required('admin')
def delete_admin(request, admin_id):
    """Delete an admin account — cannot delete your own account."""
    if request.method == 'POST':
        if admin_id == request.user.id:
            messages.error(request, 'You cannot delete your own admin account.')
        else:
            try:
                user = get_object_or_404(User, id=admin_id, is_superuser=True)
                name = user.get_full_name() or user.username
                user.delete()
                messages.success(request, f'Admin account "{name}" deleted.')
            except Exception:
                logger.exception("Failed to delete admin %s", admin_id)
                messages.error(request, "Couldn't delete admin. An unexpected error occurred.")
    return redirect('create_admin')


@role_required('admin')
def update_admin_photo(request, admin_id):
    """Allow an admin to update or upload their profile photo."""
    if request.method == 'POST':
        admin_user = get_object_or_404(User, id=admin_id, is_superuser=True)
        if request.user.id != admin_user.id and not request.user.is_superuser:
            messages.error(request, "Permission denied to update this admin's photo.")
            return redirect('create_admin')

        photo = request.FILES.get('photo')
        if photo:
            try:
                profile, created = AdminProfile.objects.get_or_create(user=admin_user)
                profile.photo = photo
                profile.save()
                messages.success(request, f'Profile photo updated for {admin_user.get_full_name() or admin_user.username}.')
            except Exception:
                logger.exception("Failed to update photo for admin %s", admin_id)
                messages.error(request, "Could not update photo. An unexpected error occurred.")
        else:
            messages.error(request, 'No photo file provided.')
    return redirect('create_admin')


@role_required('admin')
def admin_audit_log(request):
    """List and search system audit log records."""
    from resultapp.models import AuditLog
    from django.db.models import Q
    logs = AuditLog.objects.all().select_related('actor')
    q = request.GET.get('q', '').strip()
    if q:
        logs = logs.filter(
            Q(actor__username__icontains=q) |
            Q(action__icontains=q) |
            Q(target_model__icontains=q) |
            Q(target_id__icontains=q) |
            Q(ip_address__icontains=q)
        )
    page_obj = paginate(request, logs, per_page=15)
    return render(request, 'admin/audit_log.html', {'logs': page_obj, 'page_obj': page_obj, 'q': q})

