import csv
import io
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from .decorators import role_required
from django.http import StreamingHttpResponse

from resultapp.models import Student, Result, Subject

logger = logging.getLogger(__name__)


@role_required('admin')
def export_students_csv(request):
    """Download all students as a CSV file."""
    def generate():
        writer_buffer = io.StringIO()
        writer = csv.writer(writer_buffer)
        writer.writerow(['Roll ID', 'Name', 'Email', 'Gender', 'DOB', 'Class', 'Section', 'Branch', 'Status'])
        yield writer_buffer.getvalue()
        writer_buffer.seek(0); writer_buffer.truncate()

        for s in Student.objects.select_related('student_class__branch').all().order_by('name'):
            cls = s.student_class
            writer.writerow([
                s.roll_id, s.name, s.email, s.gender, s.dob,
                cls.class_name if cls else '',
                cls.section if cls else '',
                cls.branch.branch_name if cls and cls.branch else '',
                'Active' if s.status else 'Inactive',
            ])
            yield writer_buffer.getvalue()
            writer_buffer.seek(0); writer_buffer.truncate()

    response = StreamingHttpResponse(generate(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="srms_students.csv"'
    return response


@role_required('admin')
def export_results_csv(request):
    """Download all results as a CSV file."""
    def generate():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([
            'Roll ID', 'Student Name', 'Class', 'Section', 'Branch',
            'Subject Code', 'Subject Name', 'Credits',
            'Theory (30)', 'Internal (20)', 'Practical (25)', 'Oral (25)',
            'Total Obtained', 'Total Max', 'Percentage', 'Grade', 'Status',
        ])
        yield buf.getvalue(); buf.seek(0); buf.truncate()

        qs = Result.objects.select_related(
            'student', 'student_class__branch', 'subject'
        ).order_by('student__name', 'subject__subject_name')
        for r in qs:
            cls = r.student_class
            w.writerow([
                r.student.roll_id if r.student else '',
                r.student.name if r.student else '',
                cls.class_name if cls else '',
                cls.section if cls else '',
                cls.branch.branch_name if cls and cls.branch else '',
                r.subject.subject_code if r.subject else '',
                r.subject.subject_name if r.subject else '',
                r.subject.credits if r.subject else '',
                r.theory_marks, r.internal_marks,
                r.practical_marks if r.practical_marks is not None else '',
                r.oral_marks if r.oral_marks is not None else '',
                r.total_obtained, r.total_max,
                r.subject_percentage, r.nep_grade,
                'PASS' if r.is_subject_pass else 'FAIL',
            ])
            yield buf.getvalue(); buf.seek(0); buf.truncate()

    response = StreamingHttpResponse(generate(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="srms_results.csv"'
    return response


@role_required('admin')
def import_results_csv(request):
    """POST: parse uploaded CSV, validate rows, create Results. Returns error report."""
    context = {'import_errors': request.session.pop('import_errors', []),
               'import_success_count': request.session.pop('import_success_count', 0),
               'import_attempted': request.session.pop('import_attempted', False)}

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded = csv_file.read().decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(decoded))

        errors = []
        success = 0
        for row_num, row in enumerate(reader, start=2):
            try:
                roll_id    = (row.get('Roll ID') or '').strip()
                subj_code  = (row.get('Subject Code') or '').strip()
                theory     = int((row.get('Theory (30)') or '0').strip() or 0)
                internal   = int((row.get('Internal (20)') or '0').strip() or 0)
                practical  = row.get('Practical (25)', '').strip()
                oral       = row.get('Oral (25)', '').strip()
                practical  = int(practical) if practical else None
                oral       = int(oral) if oral else None

                student = Student.objects.filter(roll_id=roll_id).first()
                if not student:
                    errors.append({'row': row_num, 'roll': roll_id, 'error': f'Student with Roll ID "{roll_id}" not found.'})
                    continue
                subject = Subject.objects.filter(subject_code=subj_code).first()
                if not subject:
                    errors.append({'row': row_num, 'roll': roll_id, 'error': f'Subject with code "{subj_code}" not found.'})
                    continue
                if not (0 <= theory <= 30):
                    errors.append({'row': row_num, 'roll': roll_id, 'error': f'Theory marks {theory} out of range (0–30).'})
                    continue
                if not (0 <= internal <= 20):
                    errors.append({'row': row_num, 'roll': roll_id, 'error': f'Internal marks {internal} out of range (0–20).'})
                    continue

                Result.objects.update_or_create(
                    student=student,
                    subject=subject,
                    student_class=student.student_class,
                    defaults={
                        'theory_marks': theory,
                        'internal_marks': internal,
                        'practical_marks': practical,
                        'oral_marks': oral,
                    }
                )
                success += 1
            except (ValueError, TypeError) as ve:
                errors.append({'row': row_num, 'roll': row.get('Roll ID', '?'), 'error': f'Data format error: {ve}'})
            except Exception as ex:
                logger.exception("Unexpected error importing result row %s", row_num)
                errors.append({'row': row_num, 'roll': row.get('Roll ID', '?'), 'error': 'An unexpected system error occurred.'})

        request.session['import_errors'] = errors
        request.session['import_success_count'] = success
        request.session['import_attempted'] = True

        if errors:
            messages.warning(request, f'Import complete: {success} rows saved, {len(errors)} row(s) had errors.')
        else:
            messages.success(request, f'Import complete: {success} results saved successfully.')
        return redirect('import_export')

    return render(request, 'admin/import_export.html', context)


@role_required('admin')
def import_export(request):
    """Landing page for import/export UI."""
    context = {
        'import_errors': request.session.pop('import_errors', []),
        'import_success_count': request.session.pop('import_success_count', 0),
        'import_attempted': request.session.pop('import_attempted', False),
    }
    return render(request, 'admin/import_export.html', context)
