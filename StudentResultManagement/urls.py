# StudentResultManagement/urls.py (Main project URLs)

from django.contrib import admin
from django.urls import path, include
from resultapp.views import *
from django.conf import settings
from django.conf.urls.static import static

from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='api-student')
router.register(r'results', ResultViewSet, basename='api-result')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='home'),
    path('login/', login_page, name='login'),  # unified — handles admin/teacher/parent
    path('admin-login/', RedirectView.as_view(pattern_name='login', permanent=True), name='admin-login'),
    path('admin-google-login/', admin_google_login, name='admin_google_login'),
    path('admin-google-callback/', admin_google_callback, name='admin_google_callback'),
    path('admin-forgot-password/', admin_forgot_password, name='admin_forgot_password'),
    path('admin-verify-otp/', admin_verify_otp, name='admin_verify_otp'),
    path('admin-reset-password/', admin_reset_password, name='admin_reset_password'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),

    # Branch (programme) Management
    path('create_branch/', create_branch, name='create_branch'),
    path('manage_branches/', manage_branches, name='manage_branches'),
    path('edit_branch/<int:branch_id>/', edit_branch, name='edit_branch'),
    path('add_branch_subject/', add_branch_subject, name='add_branch_subject'),
    path('manage_branch_subjects/', manage_branch_subjects, name='manage_branch_subjects'),

    path('create_class/', create_class, name='create_class'),
    path('admin_logout/', admin_logout, name='admin_logout'),
    path('manage_classes/', manage_classes, name='manage_classes'),
    path('edit_class/<int:class_id>/', edit_class, name='edit_class'),
    path('create_subject/', create_subject, name='create_subject'),
    path('manage_subject/', manage_subject, name='manage_subject'),
    path('edit_subject/<int:subject_id>/', edit_subject, name='edit_subject'),
    path('add_subject_combination/', add_subject_combination, name='add_subject_combination'),
    path('manage_subject_combination/', manage_subject_combination, name='manage_subject_combination'),
    path('add_student/', add_student, name='add_student'),
    path('manage_students/', manage_students, name='manage_students'),
    path('edit_student/<int:student_id>/', edit_student, name='edit_student'),
    path('add_notice/', add_notice, name='add_notice'),
    path('manage_notice/', manage_notice, name='manage_notice'),
    path('add_result/', add_result, name='add_result'),
    path('get_students_subjects/', get_students_subjects, name='get_students_subjects'),
    path('get_student_percentage/', get_student_percentage, name='get_student_percentage'),
    path('manage_result/', manage_result, name='manage_result'),
    path('edit_result/<int:stid>/', edit_result, name='edit_result'),
    path('change_password/', change_password, name='change_password'),
    path('search_result/', search_result, name='search_result'),
    path('check_result/', check_result, name='check_result'),
    path('notice_detail/<int:notice_id>/', notice_detail, name='notice_detail'),

    # Parent Portal URLs
    path('parent/login/', RedirectView.as_view(pattern_name='login', permanent=True), name='parent_login'),  # redirect — use /login/
    path('parent/logout/', parent_logout, name='parent_logout'),
    path('parent/dashboard/', parent_dashboard, name='parent_dashboard'),
    path('parent/attendance/', parent_view_attendance, name='parent_attendance'),
    path('parent/attendance/export/csv/', export_parent_attendance_csv, name='export_parent_attendance_csv'),
    path('parent/results/', parent_view_results, name='parent_results'),
    path('parent/progress/', parent_view_progress, name='parent_progress'),
    path('parent/profile/', parent_profile, name='parent_profile'),
    # New parent features
    path('parent/notices/', parent_notices, name='parent_notices'),
    path('parent/performance/', parent_performance, name='parent_performance'),
    path('parent/change-password/', parent_change_password, name='parent_change_password'),
    path('parent/timetable/', parent_timetable, name='parent_timetable'),
    path('parent/result-card/', parent_result_card, name='parent_result_card'),
    path('parent/result-card/download/', parent_download_result_pdf, name='parent_download_result_pdf'),
    path('parent/consolidated-marksheet/', parent_consolidated_marksheet, name='parent_consolidated_marksheet'),
    path('parent/consolidated-marksheet/download/', parent_download_consolidated_marksheet_pdf, name='parent_download_consolidated_marksheet_pdf'),
    path('parent/exams/', parent_exams, name='parent_exams'),

    # Admin Parent Management URLs
    path('manage/create-parent/', create_parent_account, name='create_parent_account'),
    path('manage/manage-parents/', manage_parents, name='manage_parents'),
    path('manage/add-attendance/', add_attendance, name='add_attendance'),
    path('manage/attendance-reports/', admin_attendance_reports, name='admin_attendance_reports'),
    path('manage/attendance-reports/export/', export_attendance_reports_csv, name='export_attendance_reports_csv'),
    path('manage/add-progress-report/', add_progress_report, name='add_progress_report'),

    # Analytics — must NOT start with 'admin/' (conflicts with Django admin catch-all)
    path('portal/analytics/', admin_analytics, name='admin_analytics'),
    path('get-holidays/', get_holidays, name='get_holidays'),

    # Admin Management
    path('manage/create-admin/', create_admin, name='create_admin'),
    path('manage/delete-admin/<int:admin_id>/', delete_admin, name='delete_admin'),
    path('manage/update-admin-photo/<int:admin_id>/', update_admin_photo, name='update_admin_photo'),

    # Teacher Management (admin-side)
    path('manage/create-teacher/', create_teacher, name='create_teacher'),
    path('manage/delete-teacher/<int:teacher_id>/', delete_teacher, name='delete_teacher'),

    # Teacher Portal
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', teacher_students, name='teacher_students'),
    path('teacher/results/', teacher_results, name='teacher_results'),
    path('teacher/logout/', teacher_logout, name='teacher_logout'),

    path('admin-panel/audit-log/', admin_audit_log, name='admin_audit_log'),

    # Import / Export
    path('portal/import-export/', import_export, name='import_export'),
    path('portal/export-students/', export_students_csv, name='export_students_csv'),
    path('portal/export-results/', export_results_csv, name='export_results_csv'),
    path('portal/import-results/', import_results_csv, name='import_results_csv'),

    # Chatbot
    path('chatbot/', chatbot_api, name='chatbot_api'),

    # REST API v1
    path('api/v1/', include(router.urls)),
    path('api/v1/token/', obtain_auth_token, name='api_token'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)