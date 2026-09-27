from .decorators import role_required
from .auth import (
    admin_login, admin_logout, resolve_teacher, login_page,
    admin_google_login, admin_google_callback, parent_login,
    parent_logout, teacher_logout, change_password, admin_forgot_password,
    admin_verify_otp, admin_reset_password, parent_change_password
)
from .admin_dashboard import (
    index, notice_detail, admin_dashboard, create_branch, manage_branches,
    edit_branch, add_branch_subject, manage_branch_subjects, create_class,
    manage_classes, edit_class, create_subject, manage_subject, edit_subject,
    add_subject_combination, manage_subject_combination, add_notice,
    manage_notice, admin_analytics, create_admin, delete_admin,
    update_admin_photo, admin_audit_log
)
from .students import (
    paginate, get_grade, get_grade_point, get_sgpa, add_student,
    manage_students, edit_student, add_result, get_students_subjects,
    manage_result, edit_result, search_result, check_result,
    get_student_percentage, create_parent_account, manage_parents,
    add_attendance, add_progress_report, get_holidays,
    admin_attendance_reports, export_attendance_reports_csv
)
from .teacher import (
    teacher_dashboard, teacher_students, teacher_results,
    create_teacher, delete_teacher
)
from .parent import (
    resolve_portal_viewer, parent_dashboard, parent_view_attendance,
    parent_view_results, parent_view_progress, parent_profile,
    parent_notices, parent_performance, parent_timetable,
    parent_result_card, export_parent_attendance_csv, parent_download_result_pdf,
    parent_consolidated_marksheet, parent_download_consolidated_marksheet_pdf,
    parent_exams
)
from .import_export import (
    export_students_csv, export_results_csv, import_results_csv,
    import_export
)
from .chatbot import chatbot_api
from .api import StudentViewSet, ResultViewSet
