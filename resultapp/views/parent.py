import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg

from resultapp.models import Parent, Student, Attendance, Result, ProgressReport, SubjectCombination, Notice, Exam
from .decorators import role_required
from .students import get_grade, get_sgpa, compute_attendance_stats


def resolve_portal_viewer(user):
    """
    Resolve who is viewing the parent/student portal for a logged-in user.

    Returns (student, parent_or_none):
      - A Parent account:  (parent.student, parent)
      - A Student account (direct student login): (student, None)
      - Neither:            (None, None)
    """
    parent = Parent.objects.filter(user=user).select_related('student', 'user').first()
    if parent:
        return parent.student, parent
    student = Student.objects.filter(user=user).first()
    if student:
        return student, None
    return None, None


@role_required('parent')
def parent_dashboard(request):
    student = request.viewer_student
    parent = request.viewer_parent
    today = datetime.now().date()

    # 1. Attendance for the last 2 calendar months (60 days)
    sixty_days_ago = today - timedelta(days=60)
    stats_60d = compute_attendance_stats(student, date_from=sixty_days_ago, date_to=today)
    attendance_percentage = stats_60d['percentage']
    total_days = stats_60d['total_days']
    present_days = stats_60d['attended_days']
    absent_days = stats_60d['absent_days']
    is_low_attendance = attendance_percentage < 75.0

    # 2. Consolidated Academic Metrics (NEP 2020 Compliant)
    cms = student.get_consolidated_marksheet()
    current_sgpa = cms.get('sgpa', 0.0)
    overall_percentage = cms.get('overall_percentage', 0.0)
    current_sem = cms.get('semester', 1)
    semester_subjects = cms.get('subjects', [])
    cms_status = cms.get('status', 'PASS')

    # All results for secondary metrics
    all_results = Result.objects.filter(student=student).select_related('subject')
    recent_results = all_results.order_by('-posting_date')[:6]
    failed_subjects = [r for r in all_results if not r.is_subject_pass]

    # 3. Upcoming Exams for student's class
    upcoming_exams = list(
        Exam.objects.filter(
            student_class=student.student_class,
            exam_date__gte=today
        ).select_related('subject').order_by('exam_date')[:5]
    )
    for ex in upcoming_exams:
        ex.days_left = (ex.exam_date - today).days

    # 4. Latest Progress Report & Notices
    latest_progress = ProgressReport.objects.filter(student=student).order_by('-created_at').first()
    recent_notices = Notice.objects.all().order_by('-posting_date')[:3]

    return render(request, 'parent/dashboard.html', {
        'parent': parent,
        'student': student,
        'today': today,
        # Attendance (last 2 months)
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'attendance_percentage': attendance_percentage,
        'is_low_attendance': is_low_attendance,
        # Academics
        'current_sgpa': current_sgpa,
        'overall_percentage': overall_percentage,
        'current_sem': current_sem,
        'semester_subjects': semester_subjects,
        'cms_status': cms_status,
        'recent_results': recent_results,
        'is_failed': len(failed_subjects) > 0,
        'failed_subjects': failed_subjects,
        # Upcoming Exams & Progress
        'upcoming_exams': upcoming_exams,
        'latest_progress': latest_progress,
        'recent_notices': recent_notices,
    })


@role_required('parent')
def parent_view_attendance(request):
    """
    Enhanced attendance view with calendar heatmap support.
    Passes present_pct, absent_pct, late_pct and calendar_days for the heatmap.
    """
    import calendar
    from datetime import date as date_type

    student = request.viewer_student
    parent = request.viewer_parent

    now = datetime.now()
    selected_month = request.GET.get('month', '')
    selected_year  = request.GET.get('year',  str(now.year))
    selected_start_date = request.GET.get('start_date', '')
    selected_end_date = request.GET.get('end_date', '')

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    from .students import compute_attendance_stats
    
    if selected_start_date and selected_end_date:
        start_date = datetime.strptime(selected_start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(selected_end_date, "%Y-%m-%d").date()
        attendance_records = Attendance.objects.filter(
            student=student,
            date__range=(start_date, end_date)
        ).order_by('-date')
        stats = compute_attendance_stats(student, date_from=start_date, date_to=end_date)
        month_name = f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
        month_days = []
        calendar_days = []
        week_days = []
    else:
        if not selected_month and not selected_start_date:
            month_int = now.month
            selected_month = str(now.month)
        else:
            month_int = int(selected_month) if selected_month else None
            
        year_int = int(selected_year)
        
        attendance_records = Attendance.objects.filter(student=student, date__year=year_int)
        if month_int:
            attendance_records = attendance_records.filter(date__month=month_int)
            stats = compute_attendance_stats(student, month=month_int, year=year_int)
            month_name = calendar.month_name[month_int]
        else:
            stats = compute_attendance_stats(student, year=year_int)
            month_name = f"Year {year_int}"
            
        attendance_records = attendance_records.order_by('-date')
        
        if month_int:
            today = date_type.today()
            cal = calendar.Calendar(firstweekday=0)
            month_days = cal.monthdatescalendar(year_int, month_int)
            
            from collections import defaultdict
            date_status_map = defaultdict(set)
            for rec in attendance_records:
                date_status_map[rec.date].add(rec.status)
                
            att_lookup = {}
            for d, statuses in date_status_map.items():
                if 'present' in statuses:
                    att_lookup[d] = 'present'
                elif 'late' in statuses:
                    att_lookup[d] = 'late'
                elif 'absent' in statuses:
                    att_lookup[d] = 'absent'
                elif 'excused' in statuses:
                    att_lookup[d] = 'excused'

            calendar_days = []
            week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

            for week in month_days:
                for d in week:
                    if d.month != month_int:
                        calendar_days.append({'day': 0, 'date': None, 'status': '', 'is_today': False})
                    else:
                        status = att_lookup.get(d, '')
                        calendar_days.append({
                            'day': d.day,
                            'date': d,
                            'status': status,
                            'is_today': d == today,
                        })
        else:
            month_days = []
            calendar_days = []
            week_days = []

    total_records = stats['total_days']
    present_count = stats['present_days']
    absent_count  = stats['absent_days']
    late_count    = stats['late_days']
    excused_count = stats['excused_days']
    attendance_percentage = stats['percentage']

    def pct(val):
        return round((val / total_records * 100), 1) if total_records else 0

    present_pct = pct(present_count)
    absent_pct  = pct(absent_count)
    late_pct    = pct(late_count)

    return render(request, 'parent/attendance.html', {
        'parent': parent,
        'student': student,
        'attendance_records': attendance_records,
        'total_records': total_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'present_pct': present_pct,
        'absent_pct': absent_pct,
        'late_pct': late_pct,
        'attendance_percentage': attendance_percentage,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_start_date': selected_start_date,
        'selected_end_date': selected_end_date,
        'month_choices': month_choices,
        'calendar_days': calendar_days,
        'calendar_weeks': month_days,
        'week_days': week_days,
        'month_name': month_name,
    })


@role_required('parent')
def parent_view_results(request):
    student = request.viewer_student
    parent = request.viewer_parent

    from resultapp.models import BranchSubject, Exam, Student, Notice
    results = Result.objects.filter(student=student).select_related('subject').order_by('-posting_date')

    failed_subjects = [r for r in results if not r.is_subject_pass]
    passed_subjects = [r for r in results if r.is_subject_pass]
    is_failed = len(failed_subjects) > 0

    if results.exists():
        total_marks = sum(r.total_obtained for r in results)
        max_marks   = sum(r.total_max for r in results)
        percentage  = round((total_marks / max_marks * 100) if max_marks > 0 else 0, 2)
        avg_marks   = round(total_marks / len(results), 2) if results else 0
        grade = get_grade(percentage, is_failed)
    else:
        total_marks = max_marks = percentage = avg_marks = 0
        grade = 'N/A'

    # 1. SGPA (0-10 scale)
    sgpa = get_sgpa(results)

    # 2. Class Rank Calculation
    class_students = Student.objects.filter(student_class=student.student_class)
    class_size = class_students.count()
    student_rankings = []
    for s in class_students:
        s_results = Result.objects.filter(student=s)
        s_sgpa = get_sgpa(s_results) if s_results.exists() else 0.0
        student_rankings.append((s.id, s_sgpa))
    student_rankings.sort(key=lambda x: x[1], reverse=True)
    class_rank = 1
    for idx, (s_id, score) in enumerate(student_rankings):
        if s_id == student.id:
            class_rank = idx + 1
            break

    # 3. Passed subjects ratio
    passed_count = len(passed_subjects)
    total_subjects = len(results)

    # 4. Best Subject
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

    # 5. Semester Derivation & Trend Chart
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
    for r in results:
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
        class_results = Result.objects.filter(
            student__in=class_students,
            semester=sem
        )
        if not class_results.exists():
            all_class_res = Result.objects.filter(student__in=class_students).select_related('student__student_class__branch', 'subject')
            sem_class_res = [cr for cr in all_class_res if get_result_semester(cr) == sem]
            class_trend.append(get_sgpa(sem_class_res))
        else:
            class_trend.append(get_sgpa(class_results))

    # 6. Radar Chart & Bar Chart lists
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

    # 7. School-wide Top Performers ranking
    all_active_students = Student.objects.filter(status=1)
    school_rankings = []
    for s in all_active_students:
        s_results = Result.objects.filter(student=s)
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

    # 8. Upcoming Exams
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

    # 9. Activity Feed (Strict Privacy)
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

    # 10. Subject Results with real trend deltas (prior result comparison)
    #     Decision: use posting_date ordering — the most-recent result per subject
    #     is current term; the one before it (by posting_date) is previous term.
    #     If no prior result exists for that subject, delta=None → template shows "—".
    detailed_results = []
    for r in results:
        # Find the immediately preceding result for the same student+subject
        prior = (
            Result.objects
            .filter(student=student, subject=r.subject, posting_date__lt=r.posting_date)
            .order_by('-posting_date')
            .first()
        )
        if prior is not None:
            delta = round(r.subject_percentage - prior.subject_percentage, 1)
        else:
            delta = None  # no prior result → omit delta arrow

        detailed_results.append({
            'subject': r.subject.subject_name if r.subject else 'Unknown',
            'code':    r.subject.subject_code if r.subject else 'SUB-001',
            'score':   r.total_obtained,
            'max':     r.total_max,
            'percentage': r.subject_percentage,
            'grade':   r.nep_grade,
            'delta':   delta,  # float or None
        })

    return render(request, 'parent/results.html', {
        'parent': parent,
        'student': student,
        'results': results,
        'total_marks': total_marks,
        'max_marks': max_marks,
        'percentage': percentage,
        'avg_marks': round(avg_marks, 2),
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
    })


@role_required('parent')
def parent_view_progress(request):
    student = request.viewer_student
    parent = request.viewer_parent

    progress_reports = ProgressReport.objects.filter(student=student).order_by('-created_at')
    return render(request, 'parent/progress.html', {
        'parent': parent,
        'student': student,
        'progress_reports': progress_reports,
    })


@role_required('parent')
def parent_profile(request):
    student = request.viewer_student
    parent = request.viewer_parent

    if request.method == 'POST' and parent:
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        email_alerts = request.POST.get('email_alerts') == 'on'
        
        parent.phone = phone
        parent.address = address
        parent.email_alerts = email_alerts
        parent.save()
        messages.success(request, "Your profile details have been updated successfully!")
        return redirect('parent_profile')

    return render(request, 'parent/profile.html', {
        'parent': parent,
        'student': student,
    })


@role_required('parent')
def export_parent_attendance_csv(request):
    import csv
    from django.http import HttpResponse
    student = request.viewer_student
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')
    
    qs = Attendance.objects.filter(student=student)
    if start_date_str and end_date_str:
        qs = qs.filter(date__range=(start_date_str, end_date_str))
    else:
        if month:
            qs = qs.filter(date__month=int(month))
        if year:
            qs = qs.filter(date__year=int(year))
            
    qs = qs.order_by('-date')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{student.roll_id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Day', 'Subject', 'Semester', 'Status', 'Remarks'])
    for rec in qs:
        writer.writerow([
            rec.date.strftime("%Y-%m-%d"),
            rec.date.strftime("%A"),
            rec.subject.subject_name if rec.subject else 'General',
            rec.semester or '',
            rec.status.capitalize(),
            rec.remarks or ''
        ])
    return response


@role_required('parent')
def parent_notices(request):
    """Parent or student can read all school notices."""
    student = request.viewer_student
    parent = request.viewer_parent

    notices = Notice.objects.all().order_by('-posting_date')
    return render(request, 'parent/notices.html', {
        'parent': parent,
        'student': student,
        'notices': notices,
    })


@role_required('parent')
def parent_performance(request):
    """Subject-wise performance chart using Chart.js."""
    student = request.viewer_student
    parent = request.viewer_parent

    results = Result.objects.filter(student=student).select_related('subject').order_by('subject__subject_name')

    labels      = [r.subject.subject_name for r in results]
    obtained    = [r.total_obtained for r in results]
    max_marks   = [r.total_max for r in results]
    percentages = [r.subject_percentage for r in results]
    grades      = [r.nep_grade for r in results]
    pass_status = [r.is_subject_pass for r in results]

    cgpa = get_sgpa(results)

    overall_pct = round(
        sum(r.total_obtained for r in results) / sum(r.total_max for r in results) * 100, 2
    ) if results else 0

    return render(request, 'parent/performance.html', {
        'parent':       parent,
        'student':      student,
        'results':      results,
        'labels':       json.dumps(labels),
        'obtained':     json.dumps(obtained),
        'max_marks':    json.dumps(max_marks),
        'percentages':  json.dumps(percentages),
        'grades':       grades,
        'pass_status':  pass_status,
        'cgpa':         cgpa,
        'overall_pct':  overall_pct,
    })


@role_required('parent')
def parent_timetable(request):
    """Show the subjects assigned to the student's class."""
    student = request.viewer_student
    parent = request.viewer_parent

    subject_combos = SubjectCombination.objects.filter(
        student_class=student.student_class,
        status=1,
    ).select_related('subject').order_by('subject__subject_name')
    return render(request, 'parent/timetable.html', {
        'parent':         parent,
        'student':        student,
        'subject_combos': subject_combos,
    })


@role_required('parent')
def parent_result_card(request):
    """Printable / downloadable result card for the student."""
    student = request.viewer_student
    parent = request.viewer_parent

    results = Result.objects.filter(student=student).select_related('subject').order_by('subject__subject_name')

    total_obtained = sum(r.total_obtained for r in results)
    total_max      = sum(r.total_max for r in results)
    overall_pct    = round((total_obtained / total_max * 100) if total_max > 0 else 0, 2)
    failed_any     = any(not r.is_subject_pass for r in results)

    cgpa           = get_sgpa(results)
    overall_grade  = get_grade(overall_pct, failed_any)

    return render(request, 'parent/result_card.html', {
        'parent':          parent,
        'student':         student,
        'results':         results,
        'total_obtained':  total_obtained,
        'total_max':       total_max,
        'overall_pct':     overall_pct,
        'overall_grade':   overall_grade,
        'cgpa':            cgpa,
        'failed_any':      failed_any,
    })


@role_required('parent')
def parent_download_result_pdf(request):
    """Generate and download a PDF version of the student's result card."""
    import io
    from django.http import HttpResponse
    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from resultapp.views.students import get_sgpa, get_grade

    student = request.viewer_student
    parent = request.viewer_parent

    results = Result.objects.filter(student=student).select_related('subject').order_by('subject__subject_name')

    total_obtained = sum(r.total_obtained for r in results)
    total_max      = sum(r.total_max for r in results)
    overall_pct    = round((total_obtained / total_max * 100) if total_max > 0 else 0, 2)
    failed_any     = any(not r.is_subject_pass for r in results)

    cgpa           = get_sgpa(results)
    overall_grade  = get_grade(overall_pct, failed_any)

    context = {
        'parent':          parent,
        'student':         student,
        'results':         results,
        'total_obtained':  total_obtained,
        'total_max':       total_max,
        'overall_pct':     overall_pct,
        'overall_grade':   overall_grade,
        'cgpa':            cgpa,
        'failed_any':      failed_any,
        'is_pdf':          True,
    }

    import re

    template = get_template('parent/result_card_pdf.html')
    html = template.render(context)

    # xhtml2pdf does not support @keyframes or CSS animation properties.
    # Strip them out before passing HTML to pisa to prevent CSSParseError.
    # Remove @keyframes blocks (including nested braces)
    html = re.sub(r'@keyframes\s+[\w-]+\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', html, flags=re.DOTALL)
    # Remove animation shorthand and animation-* properties
    html = re.sub(r'\banimation(?:-[\w]+)?\s*:[^;]+;', '', html, flags=re.DOTALL)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("utf-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Result_Card_{student.roll_id}.pdf"'
        return response
        
    return HttpResponse("Error rendering PDF", status=400)


@role_required('parent')
def parent_consolidated_marksheet(request):
    """
    Consolidated Marksheet view aggregating all subjects for a student
    for the selected semester with full NEP 2020 breakdown.
    """
    student = request.viewer_student
    parent = request.viewer_parent

    selected_sem = request.GET.get('semester')
    marksheet_data = student.get_consolidated_marksheet(semester=selected_sem)

    return render(request, 'parent/consolidated_marksheet.html', {
        'parent': parent,
        'student': student,
        'marksheet': marksheet_data,
        'selected_semester': marksheet_data['semester'],
        'available_semesters': marksheet_data['available_semesters'],
    })


@role_required('parent')
def parent_download_consolidated_marksheet_pdf(request):
    """
    Generate and download official PDF Consolidated Marksheet for a student.
    """
    import io
    import re
    from django.http import HttpResponse
    from django.template.loader import get_template
    from xhtml2pdf import pisa

    student = request.viewer_student
    parent = request.viewer_parent

    selected_sem = request.GET.get('semester')
    marksheet_data = student.get_consolidated_marksheet(semester=selected_sem)

    context = {
        'parent': parent,
        'student': student,
        'marksheet': marksheet_data,
        'is_pdf': True,
    }

    template = get_template('parent/consolidated_marksheet_pdf.html')
    html = template.render(context)

    # Strip animations/keyframes for xhtml2pdf compatibility
    html = re.sub(r'@keyframes\s+[\w-]+\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', html, flags=re.DOTALL)
    html = re.sub(r'\banimation(?:-[\w]+)?\s*:[^;]+;', '', html, flags=re.DOTALL)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("utf-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Consolidated_Marksheet_{student.roll_id}_Sem{marksheet_data["semester"]}.pdf"'
        return response

    return HttpResponse("Error rendering PDF", status=400)


@role_required('parent')
def parent_exams(request):
    """
    Dedicated view for parents to see complete upcoming and past exam schedules
    for their student's enrolled class.
    """
    student = request.viewer_student
    parent = request.viewer_parent
    today = datetime.now().date()

    exams = Exam.objects.filter(
        student_class=student.student_class
    ).select_related('subject', 'student_class').order_by('exam_date')

    upcoming_list = []
    past_list = []
    for ex in exams:
        ex.days_left = (ex.exam_date - today).days
        if ex.exam_date >= today:
            upcoming_list.append(ex)
        else:
            past_list.append(ex)

    return render(request, 'parent/exams.html', {
        'parent': parent,
        'student': student,
        'upcoming_exams': upcoming_list,
        'past_exams': past_list,
        'today': today,
    })


