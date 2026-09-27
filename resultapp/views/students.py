import logging
import calendar
import csv
import io
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .decorators import role_required
from django.contrib import messages
from django.db.models import Avg, Q, Count
from django.db import IntegrityError, transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.core.mail import send_mail
from django.urls import reverse

from resultapp.models import (
    Student, Class, Subject, Result, SubjectCombination, BranchSubject,
    Parent, Attendance, ProgressReport, Notice, Branch
)

logger = logging.getLogger(__name__)


def paginate(request, object_list, per_page=10):
    from django.core.paginator import Paginator
    paginator = Paginator(object_list, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_grade(percentage, is_failed):
    """Mumbai University NEP 2020 — UGC 10-point grading scale"""
    if is_failed:
        return 'F'
    if percentage >= 80:  return 'O'
    if percentage >= 70:  return 'A+'
    if percentage >= 60:  return 'A'
    if percentage >= 55:  return 'B+'
    if percentage >= 50:  return 'B'
    if percentage >= 45:  return 'C'
    if percentage >= 40:  return 'D'
    return 'F'


def get_grade_point(grade):
    return {'O': 10, 'A+': 9, 'A': 8, 'B+': 7, 'B': 6, 'C': 5, 'D': 4, 'F': 0}.get(grade, 0)


def get_sgpa(results):
    """
    NEP 2020 credit-weighted SGPA/CGPA formula:
        SGPA = Σ(credit × grade_point) / Σ(credit)
    Reads real credit value from each Subject, defaulting to 4 only if missing/null.
    """
    results = list(results)
    if not results:
        return 0.0
    total_credits = 0
    weighted_points = 0
    for r in results:
        credits_val = r.subject.credits if (r.subject and r.subject.credits is not None) else 4
        total_credits += credits_val
        weighted_points += r.nep_grade_point * credits_val
    if total_credits == 0:
        return 0.0
    return round(weighted_points / total_credits, 2)


def compute_attendance_stats(student, date_from=None, date_to=None, month=None, year=None):
    """
    Computes attendance statistics for a single student by grouping records by date.
    
    Priority Rule for Day-level Status Calculation:
    - If 'present' is in the statuses for a day, the day counts as present.
    - Else if 'late' is in the statuses for a day, the day counts as late.
    - Else if 'absent' is in the statuses for a day, the day counts as absent.
    - Otherwise (all are 'excused'), the day counts as excused.
    
    Status weight rules:
    - Present/Late: counts as attended (1 day present / 1 day total).
    - Absent: counts against the student (0 days present / 1 day total).
    - Excused: ignored entirely (0 days present / 0 days total).
    """
    from collections import defaultdict
    qs = Attendance.objects.filter(student=student)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if month:
        qs = qs.filter(date__month=month)
    if year:
        qs = qs.filter(date__year=year)

    date_statuses = defaultdict(set)
    for record in qs:
        date_statuses[record.date].add(record.status)

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

    percentage = round((present_days + late_days) / total_days * 100, 2) if total_days > 0 else 0.0

    return {
        'total_days': total_days,
        'present_days': present_days,
        'late_days': late_days,
        'absent_days': absent_days,
        'excused_days': excused_days,
        'attended_days': present_days + late_days,
        'percentage': percentage,
    }



@role_required('admin')
def add_student(request):
    classes = Class.objects.all()
    if request.method == 'POST':
        try:
            student_class = get_object_or_404(Class, id=request.POST.get('class'))
            photo_file = request.FILES.get('photo')
            Student.objects.create(
                name=request.POST.get('fullname'),
                roll_id=request.POST.get('rollid'),
                email=request.POST.get('emailid'),
                gender=request.POST.get('gender'),
                dob=request.POST.get('dob') or None,
                student_class=student_class,
                photo=photo_file,
                phone=request.POST.get('phone', '').strip() or None,
                address=request.POST.get('address', '').strip() or None,
                emergency_contact_name=request.POST.get('emergency_contact_name', '').strip() or None,
                emergency_contact_phone=request.POST.get('emergency_contact_phone', '').strip() or None,
                blood_group=request.POST.get('blood_group', '').strip() or None,
            )
            messages.success(request, "Student info added successfully!")
        except IntegrityError:
            messages.error(request, "A student with that roll number or email already exists.")
        except Exception:
            logger.exception("Failed to add student")
            messages.error(request, "Couldn't add the student. An unexpected error occurred.")
        return redirect('add_student')
    return render(request, 'add_student.html', {'classes': classes})


@role_required('admin')
def manage_students(request):
    if request.method == 'POST':
        if request.POST.get('delete'):
            try:
                student_obj = get_object_or_404(Student, id=request.POST.get('delete'))
                student_obj.delete()
                messages.success(request, "Student deleted successfully!")
            except Exception:
                logger.exception("Failed to delete student")
                messages.error(request, "Couldn't delete the student. An unexpected error occurred.")
            return redirect('manage_students')
            
        elif request.POST.get('deactivate'):
            try:
                student_obj = get_object_or_404(Student, id=request.POST.get('deactivate'))
                student_obj.status = 0
                student_obj.save()
                messages.success(request, f"Student '{student_obj.name}' deactivated successfully!")
            except Exception:
                logger.exception("Failed to deactivate student")
                messages.error(request, "Couldn't deactivate the student. An unexpected error occurred.")
            return redirect('manage_students')
            
        elif request.POST.get('activate'):
            try:
                student_obj = get_object_or_404(Student, id=request.POST.get('activate'))
                student_obj.status = 1
                student_obj.save()
                messages.success(request, f"Student '{student_obj.name}' activated successfully!")
            except Exception:
                logger.exception("Failed to activate student")
                messages.error(request, "Couldn't activate the student. An unexpected error occurred.")
            return redirect('manage_students')

    # Query params
    status_filter = request.GET.get('status', 'active')
    selected_branch_id = request.GET.get('branch', '')
    attendance_filter = request.GET.get('attendance_filter', '')
    q = request.GET.get('q', '').strip()

    students = Student.objects.select_related('student_class', 'student_class__branch').all().order_by('name')

    if status_filter == 'active':
        students = students.filter(status=1)
    elif status_filter == 'inactive':
        students = students.filter(status=0)

    if selected_branch_id:
        students = students.filter(student_class__branch_id=selected_branch_id)

    if q:
        students = students.filter(
            Q(name__icontains=q) | Q(roll_id__icontains=q) | Q(email__icontains=q) |
            Q(student_class__class_name__icontains=q) | Q(student_class__section__icontains=q)
        )

    students_list = list(students)
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    for s in students_list:
        s.attendance_stats_30d = compute_attendance_stats(s, date_from=thirty_days_ago)

    # Filter by attendance in python
    if attendance_filter:
        filtered_list = []
        for s in students_list:
            pct = s.attendance_stats_30d['percentage']
            if attendance_filter == 'at_risk':
                if pct < 75.0:
                    filtered_list.append(s)
            elif attendance_filter == 'excellent':
                if pct >= 90.0 and s.attendance_stats_30d['total_days'] > 0:
                    filtered_list.append(s)
        students_list = filtered_list

    branches = Branch.objects.filter(status=1)
    page_obj = paginate(request, students_list)
    
    return render(request, 'manage_students.html', {
        'students': page_obj,
        'page_obj': page_obj,
        'q': q,
        'status_filter': status_filter,
        'selected_branch_id': selected_branch_id,
        'attendance_filter': attendance_filter,
        'branches': branches,
    })


@role_required('admin')
def edit_student(request, student_id):
    student_obj = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        try:
            if request.FILES.get('photo'):
                student_obj.photo = request.FILES.get('photo')
            student_obj.name = request.POST.get('fullname')
            student_obj.roll_id = request.POST.get('rollid')
            student_obj.email = request.POST.get('emailid')
            student_obj.gender = request.POST.get('gender')
            student_obj.dob = request.POST.get('dob') or None
            student_obj.status = int(request.POST.get('status'))
            student_obj.phone = request.POST.get('phone', '').strip() or None
            student_obj.address = request.POST.get('address', '').strip() or None
            student_obj.emergency_contact_name = request.POST.get('emergency_contact_name', '').strip() or None
            student_obj.emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip() or None
            student_obj.blood_group = request.POST.get('blood_group', '').strip() or None
            student_obj.save()
            messages.success(request, "Student updated successfully!")
        except IntegrityError:
            messages.error(request, "Another student already uses that roll number or email.")
        except Exception:
            logger.exception("Failed to edit student %s", student_id)
            messages.error(request, "Couldn't update the student. An unexpected error occurred.")
        return redirect('manage_students')
    return render(request, 'edit_student.html', {
        'student_obj': student_obj,
        'classes': Class.objects.select_related('branch').order_by('branch__branch_name', 'class_numeric', 'section'),
    })


@role_required('admin')
def add_result(request):
    classes = Class.objects.all()
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class')
            student_id = request.POST.get('studentid')
            semester_id = request.POST.get('semester') or 1
            subject_ids = set()
            for key in request.POST:
                for prefix in ('theory_', 'internal_', 'practical_', 'oral_'):
                    if key.startswith(prefix):
                        subject_ids.add(key.split('_', 1)[1])

            for subject_id in subject_ids:
                theory_val   = request.POST.get(f'theory_{subject_id}')
                internal_val = request.POST.get(f'internal_{subject_id}')
                practical_val= request.POST.get(f'practical_{subject_id}') or None
                oral_val     = request.POST.get(f'oral_{subject_id}') or None

                Result.objects.create(
                    student_id=student_id,
                    student_class_id=class_id,
                    subject_id=subject_id,
                    semester=int(semester_id),
                    theory_marks=int(theory_val or 0),
                    internal_marks=int(internal_val or 0),
                    practical_marks=int(practical_val) if practical_val else None,
                    oral_marks=int(oral_val) if oral_val else None,
                )

            student = get_object_or_404(Student, id=student_id)
        except ValueError:
            messages.error(request, "Marks must be whole numbers — please check each field and try again.")
            return redirect('add_result')
        except Exception:
            logger.exception("Failed to save result")
            messages.error(request, "Couldn't save the result. An unexpected error occurred.")
            return redirect('add_result')

        try:
            if student.email:
                send_mail(
                    subject='Your Result Has Been Added - SRMS',
                    message=(
                        f'Dear {student.name},\n\nYour result has been added successfully by the school.\n\n'
                        'Please visit the school portal to check your full result.\n\n'
                        f'Roll ID: {student.roll_id}\nClass: {student.student_class}\n\nRegards,\nSRMS College'
                    ),
                    from_email=None,
                    recipient_list=[student.email],
                    fail_silently=True,
                )

            for parent in Parent.objects.filter(student=student).select_related('user'):
                if parent.user.email:
                    send_mail(
                        subject=f'Result Added for {student.name} - SRMS',
                        message=(
                            f'Dear {parent.user.get_full_name()},\n\n'
                            f'The result for your child {student.name} has been added.\n\n'
                            'Please login to the parent portal to view the full result.\n\nRegards,\nSRMS College'
                        ),
                        from_email=None,
                        recipient_list=[parent.user.email],
                        fail_silently=True,
                    )
                if parent.phone and request.POST.get('send_whatsapp') == '1':
                    try:
                        from resultapp.whatsapp import send_whatsapp_message
                        msg_text = f"Result Alert: The result for your child {student.name} (Roll ID: {student.roll_id}) has been published. Please login to the parent portal to view details."
                        send_whatsapp_message(parent.phone, msg_text, 'result')
                    except Exception:
                        logger.exception("Failed to send WhatsApp result alert")

            messages.success(request, "Result info added successfully!")
        except Exception:
            logger.exception("Notice added but emails failed to send")
            messages.success(request, "Result info added successfully!")
            messages.warning(request, "Note: the student/parent notification email may not have been sent.")
        return redirect('add_result')
    return render(request, 'add_result.html', {'classes': classes})


@role_required('admin')
def get_students_subjects(request):
    class_id = request.GET.get('class_id')
    semester = request.GET.get('semester')

    if class_id:
        students = list(
            Student.objects.filter(student_class_id=class_id, status=1)
            .values('id', 'name', 'roll_id')
            .order_by('roll_id', 'name')
        )

        try:
            class_obj = Class.objects.select_related('branch').get(id=class_id)
        except Class.DoesNotExist:
            return JsonResponse({'students': [], 'subjects': [], 'semesters': []})

        sc_qs = SubjectCombination.objects.filter(
            student_class_id=class_id, status=1
        ).select_related('subject')
        sc_subject_ids = [sc.subject_id for sc in sc_qs]

        branch = class_obj.branch
        branch_subjects_map = {}
        valid_semesters = set()

        if branch:
            bs_all = BranchSubject.objects.filter(branch=branch, status=1).select_related('subject')
            for bs in bs_all:
                branch_subjects_map[bs.subject_id] = bs.semester

        if sc_subject_ids:
            class_subject_ids = sc_subject_ids
            for sid in class_subject_ids:
                if sid in branch_subjects_map:
                    valid_semesters.add(branch_subjects_map[sid])
        elif branch:
            numeric = class_obj.class_numeric
            if numeric and numeric in [1, 2, 3]:
                expected_sems = [numeric * 2 - 1, numeric * 2]
                bs_year = BranchSubject.objects.filter(branch=branch, semester__in=expected_sems, status=1)
                if bs_year.exists():
                    class_subject_ids = list(bs_year.values_list('subject_id', flat=True))
                    valid_semesters.update(expected_sems)
                else:
                    class_subject_ids = list(BranchSubject.objects.filter(branch=branch, status=1).values_list('subject_id', flat=True))
                    valid_semesters.update(BranchSubject.objects.filter(branch=branch, status=1).values_list('semester', flat=True))
            else:
                class_subject_ids = list(BranchSubject.objects.filter(branch=branch, status=1).values_list('subject_id', flat=True))
                valid_semesters.update(BranchSubject.objects.filter(branch=branch, status=1).values_list('semester', flat=True))
        else:
            class_subject_ids = []

        subject_objs = Subject.objects.filter(id__in=class_subject_ids).order_by('subject_name')
        subjects = []
        for sub in subject_objs:
            sub_sem = branch_subjects_map.get(sub.id)
            if semester:
                try:
                    sem_int = int(semester)
                    if sub_sem is not None and sub_sem != sem_int:
                        continue
                except (ValueError, TypeError):
                    pass
            subjects.append({
                'id': sub.id,
                'subject_name': sub.subject_name,
                'subject_code': sub.subject_code,
                'semester': sub_sem,
            })

        sorted_semesters = sorted(list(valid_semesters))

        return JsonResponse({
            'students': students,
            'subjects': subjects,
            'semesters': sorted_semesters,
        })
    return JsonResponse({'students': [], 'subjects': [], 'semesters': []})


@role_required('admin')
def manage_result(request):
    results = Result.objects.select_related('student', 'student_class').order_by('student__name')
    q = request.GET.get('q', '').strip()
    if q:
        results = results.filter(
            Q(student__name__icontains=q) | Q(student__roll_id__icontains=q) |
            Q(student_class__class_name__icontains=q) | Q(student_class__section__icontains=q)
        )
    students = {}
    for res in results:
        stu_id = res.student.id
        if stu_id not in students:
            students[stu_id] = {
                'student': res.student,
                'class': res.student_class,
            }
    result_rows = list(students.values())
    page_obj = paginate(request, result_rows)
    return render(request, 'manage_result.html', {'results': page_obj, 'page_obj': page_obj, 'q': q})


@role_required('admin')
def edit_result(request, stid):
    student = get_object_or_404(Student, id=stid)
    results = Result.objects.filter(student=student).select_related('subject', 'student_class').order_by('semester', 'subject__subject_name')

    if request.method == 'POST':
        try:
            ids = request.POST.getlist('id[]')
            if not ids:
                ids = list(results.values_list('id', flat=True))

            for res_id in ids:
                result_obj = get_object_or_404(Result, id=res_id, student=student)

                theory_val = request.POST.get(f'theory_{res_id}')
                internal_val = request.POST.get(f'internal_{res_id}')
                practical_val = request.POST.get(f'practical_{res_id}')
                oral_val = request.POST.get(f'oral_{res_id}')

                if theory_val is not None and internal_val is not None:
                    result_obj.theory_marks = int(theory_val or 0)
                    result_obj.internal_marks = int(internal_val or 0)
                    result_obj.practical_marks = int(practical_val) if practical_val and practical_val.strip() else None
                    result_obj.oral_marks = int(oral_val) if oral_val and oral_val.strip() else None
                elif request.POST.get(f'marks_{res_id}') is not None:
                    m = int(request.POST.get(f'marks_{res_id}') or 0)
                    result_obj.theory_marks = min(30, int(round(m * 0.6)))
                    result_obj.internal_marks = max(0, min(20, m - result_obj.theory_marks))

                # save() triggers self.marks = self.total_obtained
                result_obj.save()

        except ValueError:
            messages.error(request, "Marks must be valid numbers — please verify entries and try again.")
            return redirect('edit_result', stid=stid)
        except Exception:
            logger.exception("Failed to update result")
            messages.error(request, "Failed to update results due to an unexpected error.")
            return redirect('edit_result', stid=stid)

        if student.email:
            send_mail(
                subject='Your Result Has Been Updated - SRMS',
                message=(
                    f'Dear {student.name},\n\nYour result has been updated by the school.\n\n'
                    'Please visit the school portal to check your updated result.\n\n'
                    f'Roll ID: {student.roll_id}\nClass: {student.student_class}\n\nRegards,\nSRMS College'
                ),
                from_email=None,
                recipient_list=[student.email],
                fail_silently=True,
            )

        for parent in Parent.objects.filter(student=student).select_related('user'):
            if parent.user.email:
                send_mail(
                    subject=f'Result Updated for {student.name} - SRMS',
                    message=(
                        f'Dear {parent.user.get_full_name()},\n\n'
                        f'The result for your child {student.name} has been updated.\n\n'
                        'Please login to the parent portal to view the updated result.\n\nRegards,\nSRMS College'
                    ),
                    from_email=None,
                    recipient_list=[parent.user.email],
                    fail_silently=True,
                )

        messages.success(request, "Results updated successfully!")
        return redirect('manage_result')
    return render(request, 'edit_result.html', {'student': student, 'results': results})


def search_result(request):
    classes = Class.objects.all()
    return render(request, 'search_result.html', {'classes': classes})


def check_result(request):
    if request.method == 'POST':
        rollid = request.POST.get('rollid')
        class_id = request.POST.get('class')
        semester_id = request.POST.get('semester')
        try:
            student = Student.objects.get(roll_id=rollid, student_class_id=class_id)
            
            # Fetch all results of this student for trend analytics
            all_results = Result.objects.filter(student=student).select_related('subject').order_by('-posting_date')
            
            # Fetch results filtered by semester for the main marksheet display
            results = all_results
            if semester_id:
                results = results.filter(semester=int(semester_id))

            if not results.exists():
                if semester_id:
                    messages.error(request, f"No result found for Semester {semester_id} of the provided Student ID and Class.")
                else:
                    messages.error(request, "No result found for the provided Student ID and Class.")
                return redirect('search_result')

            subject_count = results.count()

            failed_subjects = [r for r in results if not r.is_subject_pass]
            passed_subjects = [r for r in results if r.is_subject_pass]
            is_failed = len(failed_subjects) > 0

            total_obtained = sum(r.total_obtained for r in results)
            total_max      = sum(r.total_max for r in results)
            percentage     = round((total_obtained / total_max * 100) if total_max > 0 else 0, 2)
            grade          = get_grade(percentage, is_failed)
            grade_point    = get_grade_point(grade)
            sgpa           = get_sgpa(results)

            # Class size & Class Rank (based on all_results SGPA of students in the same class)
            class_students = Student.objects.filter(student_class=student.student_class)
            class_size = class_students.count()
            student_rankings = []
            for s in class_students:
                s_results = Result.objects.filter(student=s)
                if semester_id:
                    s_results = s_results.filter(semester=int(semester_id))
                s_sgpa = get_sgpa(s_results) if s_results.exists() else 0.0
                student_rankings.append((s.id, s_sgpa))
            student_rankings.sort(key=lambda x: x[1], reverse=True)
            class_rank = 1
            for idx, (s_id, score) in enumerate(student_rankings):
                if s_id == student.id:
                    class_rank = idx + 1
                    break

            passed_count = len(passed_subjects)
            total_subjects = len(results)

            # Best Subject (from current semester/results)
            best_result = None
            best_pct = -1.0
            for r in results:
                if r.subject_percentage > best_pct:
                    best_pct = r.subject_percentage
                    best_result = r
            best_subject_name = "N/A"
            best_subject_score = 0
            if best_result and best_result.subject:
                best_subject_name = best_result.subject.subject_name
                if "Computer" in best_subject_name:
                    best_subject_name = "Computer"
                elif len(best_subject_name) > 12:
                    best_subject_name = best_subject_name.split()[0]
                best_subject_score = int(best_result.total_obtained)

            # Trend Chart (always use all_results for multi-semester trend)
            def get_result_semester(r):
                if r.semester:
                    return r.semester
                if r.student.student_class and r.student.student_class.branch and r.subject:
                    bs = BranchSubject.objects.filter(
                        branch=r.student.student_class.branch,
                        subject=r.subject
                    ).first()
                    if bs:
                        return bs.semester
                return 1

            semester_results = {}
            for r in all_results:
                sem = get_result_semester(r)
                if sem not in semester_results:
                    semester_results[sem] = []
                semester_results[sem].append(r)
            
            sorted_sems = sorted(semester_results.keys())
            trend_labels = []
            student_trend = []
            class_trend = []
            
            for sem in sorted_sems:
                sem_res = semester_results[sem]
                student_trend.append(get_sgpa(sem_res))
                trend_labels.append(f"Sem {sem}")
                
                # Class average SGPA for this semester
                class_results_sem = Result.objects.filter(
                    student__in=class_students,
                    semester=sem
                )
                if not class_results_sem.exists():
                    all_class_res = Result.objects.filter(student__in=class_students).select_related('student__student_class__branch', 'subject')
                    sem_class_res = [cr for cr in all_class_res if get_result_semester(cr) == sem]
                    class_trend.append(get_sgpa(sem_class_res))
                else:
                    class_trend.append(get_sgpa(class_results_sem))

            import json
            # Radar & Bar Chart (using current results)
            radar_labels = []
            radar_data = []
            bar_labels = []
            bar_data = []
            for r in results:
                if r.subject:
                    name = r.subject.subject_name
                    short = name.split()[0]
                    if "Computer" in name:
                        short = "Computer"
                    radar_labels.append(short)
                    radar_data.append(r.subject_percentage)
                    bar_labels.append(short)
                    bar_data.append(r.subject_percentage)

            # School-wide Top Performers ranking
            all_active_students = Student.objects.filter(status=1)
            school_rankings = []
            for s in all_active_students:
                s_results = Result.objects.filter(student=s)
                if semester_id:
                    s_results = s_results.filter(semester=int(semester_id))
                if s_results.exists():
                    s_sgpa = get_sgpa(s_results)
                    school_rankings.append({
                        'name': s.name,
                        'grade': f"Grade {s.student_class.class_numeric}-{s.student_class.section}" if s.student_class else "Grade 10-A",
                        'avatar': "".join(p[0] for p in s.name.split()[:2]).upper(),
                        'gpa': f"{s_sgpa:.2f}",
                        'raw_sgpa': s_sgpa
                    })
            school_rankings.sort(key=lambda x: x['raw_sgpa'], reverse=True)
            top_performers = school_rankings[:5]

            # Upcoming Exams
            from resultapp.models import Exam
            upcoming_exams_qs = Exam.objects.filter(student_class=student.student_class).select_related('subject').order_by('exam_date')
            upcoming_exams = []
            for idx, ex in enumerate(upcoming_exams_qs):
                upcoming_exams.append({
                    'subject': ex.subject.subject_name,
                    'day': ex.exam_date.strftime("%d"),
                    'day_name': ex.exam_date.strftime("%a"),
                    'month': ex.exam_date.strftime("%b"),
                    'soon': idx == 0
                })

            # Activity Feed
            activities = []
            notices = Notice.objects.all().order_by('-posting_date')[:3]
            for n in notices:
                activities.append({
                    'text': n.title,
                    'time': n.posting_date.strftime("%d %b %Y"),
                    'type': 'warning',
                    'icon': 'fa-bullhorn'
                })
            for r in results[:3]:
                activities.append({
                    'text': f"Result published for {r.subject.subject_name if r.subject else 'Subject'}",
                    'time': r.posting_date.strftime("%d %b %Y") if r.posting_date else "Recent",
                    'type': 'success',
                    'icon': 'fa-check-circle'
                })

            # Detailed results with trend deltas
            detailed_results = []
            for r in results:
                prior = (
                    Result.objects
                    .filter(student=student, subject=r.subject, posting_date__lt=r.posting_date)
                    .order_by('-posting_date')
                    .first()
                )
                if prior is not None:
                    delta = round(r.subject_percentage - prior.subject_percentage, 1)
                else:
                    delta = None

                detailed_results.append({
                    'subject': r.subject.subject_name if r.subject else 'Unknown',
                    'code':    r.subject.subject_code if r.subject else 'SUB-001',
                    'score':   r.total_obtained,
                    'max':     r.total_max,
                    'percentage': r.subject_percentage,
                    'grade':   r.nep_grade,
                    'delta':   delta,
                })

            return render(request, 'result_page.html', {
                'student': student,
                'results': results,
                'total_marks': total_obtained,
                'max_marks': total_max,
                'percentage': percentage,
                'avg_marks': round(total_obtained / len(results) if results else 0, 2),
                'failed_subjects': failed_subjects,
                'passed_subjects': passed_subjects,
                'is_failed': is_failed,
                'grade': grade,
                'sgpa': f"{sgpa:.2f}",
                'class_rank': class_rank,
                'class_size': class_size,
                'passed_count': passed_count,
                'total_subjects': total_subjects,
                'best_subject_name': best_subject_name,
                'best_subject_score': best_subject_score,
                'trend_labels': json.dumps(trend_labels),
                'student_trend': json.dumps(student_trend),
                'class_trend': json.dumps(class_trend),
                'radar_labels': json.dumps(radar_labels),
                'radar_data': json.dumps(radar_data),
                'bar_labels': json.dumps(bar_labels),
                'bar_data': json.dumps(bar_data),
                'top_performers': top_performers,
                'upcoming_exams': upcoming_exams,
                'activities': activities,
                'detailed_results': detailed_results,
                'selected_semester': semester_id,
            })

        except Student.DoesNotExist:
            messages.error(request, f"No student found with Roll ID \"{rollid}\" in the selected class. Please check your Roll ID (e.g. FYCS001, SYCS001, TYCS001).")
            return redirect('search_result')
        except Exception:
            logger.exception("Error checking result for Roll ID %s", rollid)
            messages.error(request, "Couldn't calculate the result right now. Please try again.")
            return redirect('search_result')

    return redirect('search_result')


@role_required('admin')
def get_student_percentage(request):
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'percentage': None, 'grade': 'N/A'})
    try:
        student = Student.objects.get(id=student_id)
        results = Result.objects.filter(student=student)
        if not results.exists():
            return JsonResponse({'percentage': None, 'grade': 'N/A'})
        total_marks = sum(r.total_obtained for r in results)
        max_total   = sum(r.total_max for r in results)
        percentage  = round((total_marks / max_total) * 100 if max_total > 0 else 0, 2)
        failed_subjects = [r for r in results if not r.is_subject_pass]
        is_failed = len(failed_subjects) > 0
        return JsonResponse({'percentage': percentage, 'grade': get_grade(percentage, is_failed)})
    except Student.DoesNotExist:
        return JsonResponse({'percentage': None, 'grade': 'N/A'})
    except Exception:
        logger.exception("Error getting student percentage")
        return JsonResponse({'percentage': None, 'grade': 'N/A', 'error': 'An unexpected error occurred.'})


@role_required('admin')
def create_parent_account(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        student_id = request.POST.get('student')
        relationship = request.POST.get('relationship')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            student = get_object_or_404(Student, id=student_id)
            Parent.objects.create(
                user=user,
                phone=phone,
                address=address,
                student=student,
                relationship=relationship,
            )
        except IntegrityError:
            messages.error(request, f'The username "{username}" is already taken. Please choose another.')
            return redirect('create_parent_account')
        except Exception:
            logger.exception("Failed to create parent account")
            messages.error(request, 'Could not create the parent account. An unexpected error occurred.')
            return redirect('create_parent_account')

        try:
            if email:
                login_url = request.build_absolute_uri(reverse('parent_login'))
                send_mail(
                    subject='Your Parent Account Has Been Created - SRMS',
                    message=(
                        f'Dear {first_name} {last_name},\n\n'
                        'Your parent account has been created successfully.\n\n'
                        f'Username: {username}\n'
                        f'Login URL: {login_url}\n\n'
                        'Please use the password set by the administrator to log in. '
                        'You can change it after your first login.\n\n'
                        f'You can now track the following for {student.name}:\n'
                        '- Results & Marks\n- Attendance\n- Progress Reports\n\n'
                        'Regards,\nSRMS College'
                    ),
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=True,
                )

            messages.success(request, f'Parent account created successfully for {student.name}')
            return redirect('manage_parents')
        except Exception as e:
            messages.success(request, f'Parent account created successfully for {student.name}')
            messages.warning(request, f'Note: the welcome email may not have been sent ({str(e)}).')
            return redirect('manage_parents')

    students = Student.objects.filter(status=1)
    return render(request, 'admin/create_parent.html', {'students': students})


@role_required('admin')
def manage_parents(request):
    if request.method == 'POST':
        if request.POST.get('delete'):
            try:
                parent_obj = get_object_or_404(Parent, id=request.POST.get('delete'))
                user = parent_obj.user
                parent_obj.delete()
                user.delete()
                messages.success(request, "Parent account deleted successfully!")
            except Exception:
                logger.exception("Failed to delete parent account")
                messages.error(request, "Couldn't delete the parent account. An unexpected error occurred.")
            return redirect('manage_parents')

        elif request.POST.get('parent_id') and request.POST.get('new_password'):
            try:
                parent_id = request.POST.get('parent_id')
                new_password = request.POST.get('new_password')
                if len(new_password) < 6:
                    messages.error(request, "Password must be at least 6 characters long.")
                else:
                    parent_obj = get_object_or_404(Parent, id=parent_id)
                    user = parent_obj.user
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, f"Password for parent '{user.get_full_name() or user.username}' updated successfully!")
            except Exception:
                logger.exception("Failed to update parent password")
                messages.error(request, "Couldn't update parent password. An unexpected error occurred.")
            return redirect('manage_parents')

    parents = Parent.objects.all().select_related('user', 'student')
    return render(request, 'admin/manage_parents.html', {'parents': parents})


@role_required('admin')
def add_attendance(request):
    classes  = Class.objects.select_related('branch').all()
    branches = Branch.objects.filter(status=1)

    if request.method == 'POST':
        class_id   = request.POST.get('class')
        subject_id = request.POST.get('subject') or None
        semester   = request.POST.get('semester') or None

        try:
            students = list(Student.objects.filter(student_class_id=class_id, status=1).order_by('roll_id', 'name'))
            if not students:
                raise ValueError("No students found in the selected class.")

            subject_obj = Subject.objects.get(id=subject_id) if subject_id else None

            from_date_str = request.POST.get('from_date') or request.POST.get('date')
            to_date_str   = request.POST.get('to_date') or from_date_str
            if not from_date_str:
                raise ValueError("Please provide a valid date range.")

            from datetime import date as date_type
            from_dt = date_type.fromisoformat(from_date_str)
            to_dt   = date_type.fromisoformat(to_date_str)
            if from_dt > to_dt:
                raise ValueError("Start date must be before end date.")

            total_days = (to_dt - from_dt).days + 1
            if total_days > 200:
                raise ValueError("Date range too large (max 200 days).")

            from resultapp.models import Holiday
            import json

            # Save any new custom holidays to DB
            new_holidays_json = request.POST.get('new_holidays', '')
            if new_holidays_json:
                try:
                    new_holidays_list = json.loads(new_holidays_json)
                    for item in new_holidays_list:
                        h_date_str = item.get('date')
                        h_name = item.get('name') or "Custom Holiday"
                        if h_date_str:
                            h_dt = date_type.fromisoformat(h_date_str)
                            Holiday.objects.get_or_create(date=h_dt, defaults={'name': h_name})
                except Exception:
                    logger.exception("Failed to save new custom holidays to model")

            # Parse excluded dates list from form submission
            exclude_dates_str = request.POST.get('exclude_dates', '')
            excluded_dates = set()
            for d_str in exclude_dates_str.split(','):
                d_str = d_str.strip()
                if d_str:
                    try:
                        excluded_dates.add(date_type.fromisoformat(d_str))
                    except ValueError:
                        pass

            dates = [
                from_dt + timedelta(days=i)
                for i in range(total_days)
                if (from_dt + timedelta(days=i)).weekday() != 6
                and (from_dt + timedelta(days=i)) not in excluded_dates
            ]

            if not dates:
                raise ValueError("No working days in the selected date range after exclusions.")

            semester_int = int(semester) if semester else None

            # Collect statuses and remarks per student
            student_ids = [student.id for student in students]
            student_status_map = {}
            student_remarks_map = {}
            for student in students:
                student_status_map[student.id] = request.POST.get(f'status_{student.id}', 'present')
                student_remarks_map[student.id] = request.POST.get(f'remarks_{student.id}', '')

            # Query all existing records in a single query
            existing_records = Attendance.objects.filter(
                student_id__in=student_ids,
                date__in=dates,
                subject=subject_obj,
            )
            existing_map = {(r.student_id, r.date): r for r in existing_records}
            was_absent_set = {(r.student_id, r.date) for r in existing_records if r.status == 'absent'}

            to_create = []
            to_update = []
            new_absent_events = []

            for student in students:
                st_id = student.id
                st_status = student_status_map[st_id]
                st_remarks = student_remarks_map[st_id]

                for day in dates:
                    key = (st_id, day)
                    existing = existing_map.get(key)
                    if existing:
                        existing.status = st_status
                        existing.remarks = st_remarks
                        existing.semester = semester_int
                        to_update.append(existing)
                    else:
                        to_create.append(Attendance(
                            student=student,
                            subject=subject_obj,
                            semester=semester_int,
                            date=day,
                            status=st_status,
                            remarks=st_remarks,
                        ))

                    if st_status == 'absent' and key not in was_absent_set:
                        new_absent_events.append((student, day, st_remarks))

            with transaction.atomic():
                if to_create:
                    Attendance.objects.bulk_create(to_create, batch_size=1000)
                if to_update:
                    Attendance.objects.bulk_update(to_update, ['status', 'remarks', 'semester'], batch_size=1000)

            # Send email alerts to parents of newly absent students outside atomic block
            if new_absent_events:
                absent_students = {s.id: s for s, _, _ in new_absent_events}
                parents = Parent.objects.filter(
                    student_id__in=absent_students.keys(),
                    email_alerts=True,
                ).select_related('user', 'student')

                parent_map = {}
                for p in parents:
                    if p.user and p.user.email:
                        parent_map.setdefault(p.student_id, []).append(p)

                student_absent_days = {}
                for s, day, rem in new_absent_events:
                    student_absent_days.setdefault(s.id, []).append(str(day))

                for s_id, p_list in parent_map.items():
                    s_obj = absent_students[s_id]
                    days_str = ", ".join(sorted(student_absent_days.get(s_id, [])))
                    subj_title = subject_obj.subject_name if subject_obj else "General"
                    rem = student_remarks_map.get(s_id, '')
                    for p in p_list:
                        send_mail(
                            subject=f'Attendance Alert: {s_obj.name} was Absent - SRMS',
                            message=(
                                f'Dear {p.user.get_full_name()},\n\n'
                                f'Your child {s_obj.name} was marked ABSENT on: {days_str}.\n\n'
                                f'Subject: {subj_title}\n'
                                f'Remarks: {rem if rem else "No remarks"}\n\n'
                                'Please contact the school if you have any questions.\n\nRegards,\nSRMS School'
                            ),
                            from_email=None,
                            recipient_list=[p.user.email],
                            fail_silently=True,
                        )

            total_saved = len(to_create) + len(to_update)
            messages.success(request, f"Attendance saved: {total_saved} entries across {len(dates)} working day(s).")
            return redirect('add_attendance')

        except ValueError as e:
            messages.error(request, f"Invalid input: {str(e)}")
        except Exception:
            logger.exception("Failed to record attendance")
            messages.error(request, "Couldn't record attendance. An unexpected error occurred.")

    return render(request, 'admin/add_attendance.html', {
        'classes': classes,
        'branches': branches,
    })


# NOTE on Total Working Days: working_days_count is defined as distinct attendance dates recorded school-wide/class-wide that month.
# For mid-month admissions, this denominator includes days prior to enrollment, which can make their attendance % appear lower.
@role_required('admin')
def admin_attendance_reports(request):
    """
    Monthly Attendance Summary & Consolidated Attendance Report for Admin.
    Aggregates attendance metrics per student efficiently using Django ORM annotate/Count.
    """
    now = datetime.now()
    classes = Class.objects.select_related('branch').all().order_by('class_name', 'section')
    branches = Branch.objects.filter(status=1).order_by('branch_name')

    selected_month = request.GET.get('month', str(now.month))
    selected_year = request.GET.get('year', str(now.year))
    selected_class_id = request.GET.get('class', '')
    selected_branch_id = request.GET.get('branch', '')
    q = request.GET.get('q', '').strip()

    try:
        month_int = int(selected_month)
    except (ValueError, TypeError):
        month_int = now.month
        selected_month = str(month_int)

    try:
        year_int = int(selected_year)
    except (ValueError, TypeError):
        year_int = now.year
        selected_year = str(year_int)

    students = Student.objects.filter(status=1).select_related('student_class', 'student_class__branch').order_by('student_class__class_numeric', 'student_class__section', 'roll_id')

    if selected_class_id:
        students = students.filter(student_class_id=selected_class_id)
    elif selected_branch_id:
        students = students.filter(student_class__branch_id=selected_branch_id)

    if q:
        students = students.filter(
            Q(name__icontains=q) | Q(roll_id__icontains=q)
        )

    # Distinct working dates in that month for the selected scope
    att_scope = Attendance.objects.filter(date__year=year_int, date__month=month_int)
    if selected_class_id:
        att_scope = att_scope.filter(student__student_class_id=selected_class_id)
    elif selected_branch_id:
        att_scope = att_scope.filter(student__student_class__branch_id=selected_branch_id)

    working_days_count = att_scope.values('date').distinct().count()

    page_obj = paginate(request, students, per_page=25)

    # Single-query aggregation for the current page of students
    page_student_ids = [s.id for s in page_obj.object_list]
    student_stats = (
        Attendance.objects.filter(
            date__year=year_int,
            date__month=month_int,
            student_id__in=page_student_ids
        )
        .values('student_id')
        .annotate(
            recorded_days=Count('date', distinct=True),
            present_days=Count('date', distinct=True, filter=Q(status__in=['present', 'late'])),
            absent_days=Count('date', distinct=True, filter=Q(status='absent')),
        )
    )
    stats_map = {item['student_id']: item for item in student_stats}

    reports_data = []
    for s in page_obj.object_list:
        st = stats_map.get(s.id, {})
        rec_days = st.get('recorded_days', 0)
        p_count = st.get('present_days', 0)
        a_count = st.get('absent_days', 0)

        total_working = working_days_count if working_days_count > 0 else rec_days
        pct = round((p_count / total_working * 100), 1) if total_working > 0 else 0.0

        reports_data.append({
            'student': s,
            'working_days': total_working,
            'present_count': p_count,
            'absent_count': a_count,
            'attendance_pct': pct,
        })

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ]
    year_choices = [now.year - 1, now.year, now.year + 1]

    return render(request, 'admin/attendance_reports.html', {
        'page_obj': page_obj,
        'reports_data': reports_data,
        'classes': classes,
        'branches': branches,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_class_id': selected_class_id,
        'selected_branch_id': selected_branch_id,
        'q': q,
        'working_days_count': working_days_count,
        'month_choices': month_choices,
        'year_choices': year_choices,
        'month_name': calendar.month_name[month_int],
    })


@role_required('admin')
def export_attendance_reports_csv(request):
    """
    Export consolidated monthly attendance report to CSV.
    """
    now = datetime.now()
    selected_month = request.GET.get('month', str(now.month))
    selected_year = request.GET.get('year', str(now.year))
    selected_class_id = request.GET.get('class', '')
    selected_branch_id = request.GET.get('branch', '')
    q = request.GET.get('q', '').strip()

    month_int = int(selected_month) if selected_month.isdigit() else now.month
    year_int = int(selected_year) if selected_year.isdigit() else now.year

    students = Student.objects.filter(status=1).select_related('student_class', 'student_class__branch').order_by('student_class__class_numeric', 'student_class__section', 'roll_id')

    if selected_class_id:
        students = students.filter(student_class_id=selected_class_id)
    elif selected_branch_id:
        students = students.filter(student_class__branch_id=selected_branch_id)

    if q:
        students = students.filter(Q(name__icontains=q) | Q(roll_id__icontains=q))

    att_scope = Attendance.objects.filter(date__year=year_int, date__month=month_int)
    if selected_class_id:
        att_scope = att_scope.filter(student__student_class_id=selected_class_id)
    elif selected_branch_id:
        att_scope = att_scope.filter(student__student_class__branch_id=selected_branch_id)

    working_days_count = att_scope.values('date').distinct().count()

    student_stats = (
        Attendance.objects.filter(
            date__year=year_int,
            date__month=month_int,
            student__in=students
        )
        .values('student_id')
        .annotate(
            recorded_days=Count('date', distinct=True),
            present_days=Count('date', distinct=True, filter=Q(status__in=['present', 'late'])),
            absent_days=Count('date', distinct=True, filter=Q(status='absent')),
        )
    )
    stats_map = {item['student_id']: item for item in student_stats}

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['Roll ID', 'Student Name', 'Branch', 'Class', 'Section', 'Month', 'Year', 'Total Working Days', 'Present Count', 'Absent Count', 'Attendance %'])
        yield buf.getvalue()
        buf.seek(0); buf.truncate()

        month_label = calendar.month_name[month_int]
        for s in students:
            cls = s.student_class
            st = stats_map.get(s.id, {})
            p_count = st.get('present_days', 0)
            a_count = st.get('absent_days', 0)
            rec_days = st.get('recorded_days', 0)
            tot_work = working_days_count if working_days_count > 0 else rec_days
            pct = round((p_count / tot_work * 100), 1) if tot_work > 0 else 0.0

            writer.writerow([
                s.roll_id,
                s.name,
                cls.branch.branch_name if cls and cls.branch else '',
                cls.class_name if cls else '',
                cls.section if cls else '',
                month_label,
                year_int,
                tot_work,
                p_count,
                a_count,
                f"{pct}%",
            ])
            yield buf.getvalue()
            buf.seek(0); buf.truncate()

    response = StreamingHttpResponse(generate(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="attendance_report_{month_int}_{year_int}.csv"'
    return response


@role_required('admin')
def get_holidays(request):
    from datetime import date as date_type
    from resultapp.models import Holiday
    from django.http import JsonResponse
    
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    if not from_date_str or not to_date_str:
        return JsonResponse({'holidays': []})
        
    try:
        from_dt = date_type.fromisoformat(from_date_str)
        to_dt = date_type.fromisoformat(to_date_str)
        holidays_qs = Holiday.objects.filter(date__range=(from_dt, to_dt))
        holidays_data = [
            {'date': h.date.isoformat(), 'name': h.name}
            for h in holidays_qs
        ]
        return JsonResponse({'holidays': holidays_data})
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)


@role_required('admin')
def add_progress_report(request):
    students = Student.objects.filter(status=1)
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student')
            term = request.POST.get('term')
            overall_percentage = request.POST.get('overall_percentage')
            grade = request.POST.get('grade')
            teacher_remarks = request.POST.get('teacher_remarks')
            strengths = request.POST.get('strengths')
            areas_of_improvement = request.POST.get('areas_of_improvement')

            ProgressReport.objects.create(
                student_id=student_id,
                term=term,
                overall_percentage=overall_percentage,
                grade=grade,
                teacher_remarks=teacher_remarks,
                strengths=strengths,
                areas_of_improvement=areas_of_improvement,
            )

            student = get_object_or_404(Student, id=student_id)
        except ValueError:
            messages.error(request, "Overall percentage must be a valid number.")
            return redirect('add_progress_report')
        except Exception:
            logger.exception("Failed to save progress report")
            messages.error(request, "Couldn't save the progress report. An unexpected error occurred.")
            return redirect('add_progress_report')

        try:
            for parent in Parent.objects.filter(student=student).select_related('user'):
                if parent.user.email:
                    send_mail(
                        subject=f'Progress Report Added - {term} - SRMS',
                        message=(
                            f'Dear {parent.user.get_full_name()},\n\n'
                            f'A new progress report has been added for {student.name}.\n\n'
                            f'Term: {term}\nGrade: {grade}\nOverall Percentage: {overall_percentage}%\n'
                            f'Teacher Remarks: {teacher_remarks}\n'
                            f'Strengths: {strengths or "N/A"}\n'
                            f'Areas of Improvement: {areas_of_improvement or "N/A"}\n\n'
                            'Please login to the parent portal for more details.\n\nRegards,\nSRMS College'
                        ),
                        from_email=None,
                        recipient_list=[parent.user.email],
                        fail_silently=True,
                    )

            messages.success(request, "Progress report added successfully!")
            return redirect('add_progress_report')
        except Exception as e:
            messages.success(request, "Progress report added successfully!")
            messages.warning(request, f"Note: the parent notification email may not have been sent ({str(e)}).")
            return redirect('add_progress_report')

    return render(request, 'admin/add_progress_report.html', {'students': students})
