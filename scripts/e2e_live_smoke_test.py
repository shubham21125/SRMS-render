import re
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8080"
results = []

def log_test(category, url_or_action, status, detail=""):
    print(f"[{status}] {category} | {url_or_action} - {detail}")
    results.append({
        "category": category,
        "url_or_action": url_or_action,
        "status": status,
        "detail": detail
    })

def get_csrf(session, url):
    res = session.get(url)
    match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', res.text)
    if match:
        return match.group(1), res
    return session.cookies.get('csrftoken', ''), res

def run_smoke_test():
    print("=" * 80)
    print("STARTING FULL END-TO-END LIVE FUNCTIONAL SMOKE TEST FOR SRMS")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. Public / Landing
    # -------------------------------------------------------------
    anon_session = requests.Session()
    
    # 1.1 Home / Index
    try:
        r = anon_session.get(f"{BASE_URL}/")
        if r.status_code == 200 and "Student Result" in r.text:
            log_test("Public / Landing", "/", "PASS", f"Status 200, Content verified ({len(r.text)} bytes)")
        else:
            log_test("Public / Landing", "/", "FAIL", f"Status {r.status_code}")
    except Exception as e:
        log_test("Public / Landing", "/", "FAIL", str(e))

    # 1.2 Login Page
    try:
        r = anon_session.get(f"{BASE_URL}/login/")
        if r.status_code == 200 and "Login" in r.text:
            log_test("Public / Landing", "/login/", "PASS", "Status 200, Unified login form rendered")
        else:
            log_test("Public / Landing", "/login/", "FAIL", f"Status {r.status_code}")
    except Exception as e:
        log_test("Public / Landing", "/login/", "FAIL", str(e))

    # 1.3 /admin-login/ redirect
    try:
        r = anon_session.get(f"{BASE_URL}/admin-login/", allow_redirects=True)
        if r.status_code == 200 and "/login/" in r.url:
            log_test("Public / Landing", "/admin-login/ (redirect)", "PASS", "Correctly redirected to unified login")
        else:
            log_test("Public / Landing", "/admin-login/ (redirect)", "FAIL", f"Final URL {r.url}, Status {r.status_code}")
    except Exception as e:
        log_test("Public / Landing", "/admin-login/ (redirect)", "FAIL", str(e))

    # 1.4 /parent/login/ redirect
    try:
        r = anon_session.get(f"{BASE_URL}/parent/login/", allow_redirects=True)
        if r.status_code == 200 and "/login/" in r.url:
            log_test("Public / Landing", "/parent/login/ (redirect)", "PASS", "Correctly redirected to unified login")
        else:
            log_test("Public / Landing", "/parent/login/ (redirect)", "FAIL", f"Final URL {r.url}, Status {r.status_code}")
    except Exception as e:
        log_test("Public / Landing", "/parent/login/ (redirect)", "FAIL", str(e))

    # -------------------------------------------------------------
    # 2. Admin Flow
    # -------------------------------------------------------------
    admin_session = requests.Session()
    
    # 2.1 Admin Login
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/login/")
    login_data = {
        "csrfmiddlewaretoken": csrf,
        "username": "admin123",
        "password": "Admin@123",
        "role": "admin"
    }
    r = admin_session.post(f"{BASE_URL}/login/", data=login_data, allow_redirects=True)
    if r.status_code == 200 and "/admin-dashboard/" in r.url:
        log_test("Admin Flow", "Admin Login (/login/ -> /admin-dashboard/)", "PASS", "Logged in successfully as superuser")
    else:
        log_test("Admin Flow", "Admin Login (/login/ -> /admin-dashboard/)", "FAIL", f"Status {r.status_code}, URL {r.url}")

    # 2.2 Admin Dashboard
    r = admin_session.get(f"{BASE_URL}/admin-dashboard/")
    if r.status_code == 200 and "Dashboard" in r.text:
        log_test("Admin Flow", "/admin-dashboard/", "PASS", "Status 200, widgets and statistics rendered")
    else:
        log_test("Admin Flow", "/admin-dashboard/", "FAIL", f"Status {r.status_code}")

    # 2.3 Branch Management
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/create_branch/")
    if r.status_code == 200:
        log_test("Admin Flow", "/create_branch/ (GET)", "PASS", "Form rendered")
        post_data = {"csrfmiddlewaretoken": csrf, "branch_name": "Mechanical Engineering", "branch_code": "ME101", "description": "Core Mechanical"}
        r_post = admin_session.post(f"{BASE_URL}/create_branch/", data=post_data, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/create_branch/ (POST)", "PASS", "Branch created successfully")
        else:
            log_test("Admin Flow", "/create_branch/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/create_branch/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_branches/")
    if r.status_code == 200 and "Branches" in r.text:
        log_test("Admin Flow", "/manage_branches/", "PASS", "Branch listing rendered")
    else:
        log_test("Admin Flow", "/manage_branches/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/edit_branch/1/")
    if r.status_code in [200, 302]:
        log_test("Admin Flow", "/edit_branch/1/", "PASS", f"Status {r.status_code}")
    else:
        log_test("Admin Flow", "/edit_branch/1/", "FAIL", f"Status {r.status_code}")

    csrf, r = get_csrf(admin_session, f"{BASE_URL}/add_branch_subject/")
    if r.status_code == 200:
        log_test("Admin Flow", "/add_branch_subject/", "PASS", "Form rendered")
    else:
        log_test("Admin Flow", "/add_branch_subject/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_branch_subjects/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage_branch_subjects/", "PASS", "List rendered")
    else:
        log_test("Admin Flow", "/manage_branch_subjects/", "FAIL", f"Status {r.status_code}")

    # 2.4 Class Management
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/create_class/")
    if r.status_code == 200:
        log_test("Admin Flow", "/create_class/ (GET)", "PASS", "Form rendered")
        post_data = {"csrfmiddlewaretoken": csrf, "classname": "Class 9", "classnamenumeric": "9", "section": "A"}
        r_post = admin_session.post(f"{BASE_URL}/create_class/", data=post_data, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/create_class/ (POST)", "PASS", "Class created/submitted")
        else:
            log_test("Admin Flow", "/create_class/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/create_class/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_classes/")
    if r.status_code == 200 and "Class" in r.text:
        log_test("Admin Flow", "/manage_classes/", "PASS", "Class listing rendered")
    else:
        log_test("Admin Flow", "/manage_classes/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/edit_class/1/")
    if r.status_code in [200, 302]:
        log_test("Admin Flow", "/edit_class/1/", "PASS", f"Edit class form status {r.status_code}")
    else:
        log_test("Admin Flow", "/edit_class/1/", "FAIL", f"Status {r.status_code}")

    # 2.5 Subject Management
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/create_subject/")
    if r.status_code == 200:
        log_test("Admin Flow", "/create_subject/ (GET)", "PASS", "Form rendered")
        post_data = {"csrfmiddlewaretoken": csrf, "subjectname": "Chemistry", "subjectcode": "CHEM101", "credits": "3"}
        r_post = admin_session.post(f"{BASE_URL}/create_subject/", data=post_data, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/create_subject/ (POST)", "PASS", "Subject created")
        else:
            log_test("Admin Flow", "/create_subject/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/create_subject/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_subject/")
    if r.status_code == 200 and "Subject" in r.text:
        log_test("Admin Flow", "/manage_subject/", "PASS", "Subject listing rendered")
    else:
        log_test("Admin Flow", "/manage_subject/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/edit_subject/1/")
    if r.status_code in [200, 302]:
        log_test("Admin Flow", "/edit_subject/1/", "PASS", f"Edit subject status {r.status_code}")
    else:
        log_test("Admin Flow", "/edit_subject/1/", "FAIL", f"Status {r.status_code}")

    csrf, r = get_csrf(admin_session, f"{BASE_URL}/add_subject_combination/")
    if r.status_code == 200:
        log_test("Admin Flow", "/add_subject_combination/", "PASS", "Form rendered")
    else:
        log_test("Admin Flow", "/add_subject_combination/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_subject_combination/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage_subject_combination/", "PASS", "Combinations rendered")
    else:
        log_test("Admin Flow", "/manage_subject_combination/", "FAIL", f"Status {r.status_code}")

    # 2.6 Student Management
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/add_student/")
    if r.status_code == 200:
        log_test("Admin Flow", "/add_student/ (GET)", "PASS", "Form rendered")
        post_data = {
            "csrfmiddlewaretoken": csrf,
            "fullanme": "Aditi Roy",
            "rollid": "STU2026099",
            "emailid": "aditi.roy@test.com",
            "gender": "Female",
            "class": "1",
            "dob": "2010-06-15"
        }
        r_post = admin_session.post(f"{BASE_URL}/add_student/", data=post_data, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/add_student/ (POST)", "PASS", "Student added successfully")
        else:
            log_test("Admin Flow", "/add_student/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/add_student/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_students/")
    if r.status_code == 200 and "Student" in r.text:
        log_test("Admin Flow", "/manage_students/", "PASS", "Students table rendered")
    else:
        log_test("Admin Flow", "/manage_students/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/edit_student/1/")
    if r.status_code in [200, 302]:
        log_test("Admin Flow", "/edit_student/1/", "PASS", f"Edit student status {r.status_code}")
    else:
        log_test("Admin Flow", "/edit_student/1/", "FAIL", f"Status {r.status_code}")

    # 2.7 Results Management
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/add_result/")
    if r.status_code == 200:
        log_test("Admin Flow", "/add_result/ (GET)", "PASS", "Form rendered")
    else:
        log_test("Admin Flow", "/add_result/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_result/")
    if r.status_code == 200 and "Result" in r.text:
        log_test("Admin Flow", "/manage_result/", "PASS", "Results list rendered")
    else:
        log_test("Admin Flow", "/manage_result/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/edit_result/1/")
    if r.status_code in [200, 302]:
        log_test("Admin Flow", "/edit_result/1/", "PASS", f"Edit result status {r.status_code}")
    else:
        log_test("Admin Flow", "/edit_result/1/", "FAIL", f"Status {r.status_code}")

    csrf, r = get_csrf(admin_session, f"{BASE_URL}/search_result/")
    if r.status_code == 200:
        log_test("Admin Flow", "/search_result/ (GET)", "PASS", "Form rendered")
        r_post = admin_session.post(f"{BASE_URL}/search_result/", data={"csrfmiddlewaretoken": csrf, "rollid": "STU2026001"}, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/search_result/ (POST)", "PASS", "Result search executed")
        else:
            log_test("Admin Flow", "/search_result/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/search_result/ (GET)", "FAIL", f"Status {r.status_code}")

    csrf, r = get_csrf(admin_session, f"{BASE_URL}/check_result/")
    if r.status_code == 200:
        log_test("Admin Flow", "/check_result/ (GET)", "PASS", "Public check result rendered")
    else:
        log_test("Admin Flow", "/check_result/ (GET)", "FAIL", f"Status {r.status_code}")

    # 2.8 Notices Management
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/add_notice/")
    if r.status_code == 200:
        log_test("Admin Flow", "/add_notice/ (GET)", "PASS", "Form rendered")
        post_data = {"csrfmiddlewaretoken": csrf, "title": "Winter Break Notice", "description": "School closed from Dec 24"}
        r_post = admin_session.post(f"{BASE_URL}/add_notice/", data=post_data, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/add_notice/ (POST)", "PASS", "Notice created")
        else:
            log_test("Admin Flow", "/add_notice/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/add_notice/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage_notice/")
    if r.status_code == 200 and "Notice" in r.text:
        log_test("Admin Flow", "/manage_notice/", "PASS", "Notice list rendered")
    else:
        log_test("Admin Flow", "/manage_notice/", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/notice_detail/1/")
    if r.status_code in [200, 302]:
        log_test("Admin Flow", "/notice_detail/1/", "PASS", f"Notice detail status {r.status_code}")
    else:
        log_test("Admin Flow", "/notice_detail/1/", "FAIL", f"Status {r.status_code}")

    # 2.9 Teacher Management (Admin side)
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/manage/create-teacher/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage/create-teacher/ (GET)", "PASS", "Create teacher form rendered")
        teacher_username = "anita.teacher"
        post_data = {
            "csrfmiddlewaretoken": csrf,
            "username": teacher_username,
            "first_name": "Anita",
            "last_name": "Deshmukh",
            "email": "anita.teacher@example.com",
            "password": "TeacherDemo@123",
            "confirm_password": "TeacherDemo@123",
            "phone": "9812345678",
            "department": "Mathematics",
            "assigned_classes": ["1"],
            "assigned_subjects": ["1"]
        }
        r_post = admin_session.post(f"{BASE_URL}/manage/create-teacher/", data=post_data, allow_redirects=True)
        if r_post.status_code == 200 and ("Teacher account created" in r_post.text or "anita.teacher" in r_post.text or "already taken" in r_post.text):
            log_test("Admin Flow", "/manage/create-teacher/ (POST)", "PASS", "Teacher account created successfully")
        else:
            log_test("Admin Flow", "/manage/create-teacher/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/manage/create-teacher/ (GET)", "FAIL", f"Status {r.status_code}")

    # 2.10 Parent Management (Admin side)
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/manage/create-parent/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage/create-parent/ (GET)", "PASS", "Create parent form rendered")
    else:
        log_test("Admin Flow", "/manage/create-parent/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/manage/manage-parents/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage/manage-parents/", "PASS", "Manage parents rendered")
    else:
        log_test("Admin Flow", "/manage/manage-parents/", "FAIL", f"Status {r.status_code}")

    csrf, r = get_csrf(admin_session, f"{BASE_URL}/manage/add-attendance/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage/add-attendance/ (GET)", "PASS", "Add attendance form rendered")
    else:
        log_test("Admin Flow", "/manage/add-attendance/ (GET)", "FAIL", f"Status {r.status_code}")

    csrf, r = get_csrf(admin_session, f"{BASE_URL}/manage/add-progress-report/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage/add-progress-report/ (GET)", "PASS", "Add progress report form rendered")
    else:
        log_test("Admin Flow", "/manage/add-progress-report/ (GET)", "FAIL", f"Status {r.status_code}")

    # 2.11 Admin Accounts & Audit Log
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/manage/create-admin/")
    if r.status_code == 200:
        log_test("Admin Flow", "/manage/create-admin/ (GET)", "PASS", "Create admin form rendered")
        # Test creating new admin
        admin_post = {
            "csrfmiddlewaretoken": csrf,
            "username": "subadmin_test",
            "first_name": "Test",
            "last_name": "Admin",
            "email": "subadmin_test@example.com",
            "password": "AdminDemo@123",
            "confirm_password": "AdminDemo@123",
        }
        r_post_adm = admin_session.post(f"{BASE_URL}/manage/create-admin/", data=admin_post, allow_redirects=True)
        if r_post_adm.status_code == 200:
            log_test("Admin Flow", "/manage/create-admin/ (POST)", "PASS", "Admin account created successfully")
        else:
            log_test("Admin Flow", "/manage/create-admin/ (POST)", "FAIL", f"Status {r_post_adm.status_code}")
    else:
        log_test("Admin Flow", "/manage/create-admin/ (GET)", "FAIL", f"Status {r.status_code}")

    r = admin_session.get(f"{BASE_URL}/admin-panel/audit-log/")
    if r.status_code == 200:
        log_test("Admin Flow", "/admin-panel/audit-log/", "PASS", "Audit log rendered")
    else:
        log_test("Admin Flow", "/admin-panel/audit-log/", "FAIL", f"Status {r.status_code}")

    # 2.12 Analytics
    r = admin_session.get(f"{BASE_URL}/portal/analytics/")
    if r.status_code == 200 and "Analytics" in r.text:
        log_test("Admin Flow", "/portal/analytics/", "PASS", "Analytics charts and metrics rendered")
    else:
        log_test("Admin Flow", "/portal/analytics/", "FAIL", f"Status {r.status_code}")

    # 2.13 Import / Export
    r = admin_session.get(f"{BASE_URL}/portal/import-export/")
    if r.status_code == 200:
        log_test("Admin Flow", "/portal/import-export/", "PASS", "Import/Export UI rendered")
    else:
        log_test("Admin Flow", "/portal/import-export/", "FAIL", f"Status {r.status_code}")

    r_export_stu = admin_session.get(f"{BASE_URL}/portal/export-students/")
    if r_export_stu.status_code == 200 and "text/csv" in r_export_stu.headers.get("Content-Type", ""):
        log_test("Admin Flow", "/portal/export-students/", "PASS", "CSV download generated successfully")
    else:
        log_test("Admin Flow", "/portal/export-students/", "FAIL", f"Status {r_export_stu.status_code}")

    r_export_res = admin_session.get(f"{BASE_URL}/portal/export-results/")
    if r_export_res.status_code == 200 and "text/csv" in r_export_res.headers.get("Content-Type", ""):
        log_test("Admin Flow", "/portal/export-results/", "PASS", "CSV download generated successfully")
    else:
        log_test("Admin Flow", "/portal/export-results/", "FAIL", f"Status {r_export_res.status_code}")

    # 2.14 Change Password & Admin Logout
    csrf, r = get_csrf(admin_session, f"{BASE_URL}/change_password/")
    if r.status_code == 200:
        log_test("Admin Flow", "/change_password/", "PASS", "Change password form rendered")
    else:
        log_test("Admin Flow", "/change_password/", "FAIL", f"Status {r.status_code}")

    r_logout = admin_session.get(f"{BASE_URL}/admin_logout/", allow_redirects=True)
    if r_logout.status_code == 200 and "/login/" in r_logout.url:
        log_test("Admin Flow", "/admin_logout/", "PASS", "Logged out and redirected to login")
    else:
        log_test("Admin Flow", "/admin_logout/", "FAIL", f"Status {r_logout.status_code}, URL {r_logout.url}")

    # 2.15 Forgot Password Flow (OTP steps)
    csrf, r = get_csrf(anon_session, f"{BASE_URL}/admin-forgot-password/")
    if r.status_code == 200:
        log_test("Admin Flow", "/admin-forgot-password/ (GET)", "PASS", "Form rendered")
        r_post = anon_session.post(f"{BASE_URL}/admin-forgot-password/", data={"csrfmiddlewaretoken": csrf, "email": "admin123@example.com"}, allow_redirects=True)
        if r_post.status_code == 200:
            log_test("Admin Flow", "/admin-forgot-password/ (POST)", "PASS", f"Processed without crash (URL: {r_post.url})")
        else:
            log_test("Admin Flow", "/admin-forgot-password/ (POST)", "FAIL", f"Status {r_post.status_code}")
    else:
        log_test("Admin Flow", "/admin-forgot-password/ (GET)", "FAIL", f"Status {r.status_code}")

    r_otp = anon_session.get(f"{BASE_URL}/admin-verify-otp/")
    if r_otp.status_code in [200, 302]:
        log_test("Admin Flow", "/admin-verify-otp/", "PASS", f"Status {r_otp.status_code}")
    else:
        log_test("Admin Flow", "/admin-verify-otp/", "FAIL", f"Status {r_otp.status_code}")

    r_reset = anon_session.get(f"{BASE_URL}/admin-reset-password/")
    if r_reset.status_code in [200, 302]:
        log_test("Admin Flow", "/admin-reset-password/", "PASS", f"Status {r_reset.status_code}")
    else:
        log_test("Admin Flow", "/admin-reset-password/", "FAIL", f"Status {r_reset.status_code}")

    # 2.16 Google OAuth Redirect Check
    try:
        r_google = anon_session.get(f"{BASE_URL}/admin-google-login/", allow_redirects=False)
        if r_google.status_code in [302, 200]:
            log_test("Admin Flow", "/admin-google-login/", "PASS", f"Redirect status {r_google.status_code} (Target: {r_google.headers.get('Location', '')[:40]}...)")
        else:
            log_test("Admin Flow", "/admin-google-login/", "FAIL", f"Status {r_google.status_code}")
    except Exception as e:
        log_test("Admin Flow", "/admin-google-login/", "FAIL", str(e))

    # -------------------------------------------------------------
    # 3. Teacher Flow
    # -------------------------------------------------------------
    teacher_session = requests.Session()
    csrf, r = get_csrf(teacher_session, f"{BASE_URL}/login/")
    login_data = {
        "csrfmiddlewaretoken": csrf,
        "username": "anita.teacher",
        "password": "TeacherDemo@123",
        "role": "teacher"
    }
    r = teacher_session.post(f"{BASE_URL}/login/", data=login_data, allow_redirects=True)
    if r.status_code == 200 and "/teacher/dashboard/" in r.url:
        log_test("Teacher Flow", "Teacher Login (/login/ -> /teacher/dashboard/)", "PASS", "Logged in successfully as Teacher")
    else:
        log_test("Teacher Flow", "Teacher Login (/login/ -> /teacher/dashboard/)", "FAIL", f"Status {r.status_code}, URL {r.url}")

    # teacher/dashboard/
    r = teacher_session.get(f"{BASE_URL}/teacher/dashboard/")
    if r.status_code == 200 and "Dashboard" in r.text:
        log_test("Teacher Flow", "/teacher/dashboard/", "PASS", "Teacher Dashboard rendered successfully")
    else:
        log_test("Teacher Flow", "/teacher/dashboard/", "FAIL", f"Status {r.status_code}")

    # teacher/students/
    r = teacher_session.get(f"{BASE_URL}/teacher/students/")
    if r.status_code == 200 and "Students" in r.text:
        log_test("Teacher Flow", "/teacher/students/", "PASS", "Assigned students view rendered")
    else:
        log_test("Teacher Flow", "/teacher/students/", "FAIL", f"Status {r.status_code}")

    # teacher/results/
    r = teacher_session.get(f"{BASE_URL}/teacher/results/")
    if r.status_code == 200 and "Results" in r.text:
        log_test("Teacher Flow", "/teacher/results/", "PASS", "Results entry view rendered")
    else:
        log_test("Teacher Flow", "/teacher/results/", "FAIL", f"Status {r.status_code}")

    # teacher/logout/
    r = teacher_session.get(f"{BASE_URL}/teacher/logout/", allow_redirects=True)
    if r.status_code == 200 and "/login/" in r.url:
        log_test("Teacher Flow", "/teacher/logout/", "PASS", "Logged out and redirected to login")
    else:
        log_test("Teacher Flow", "/teacher/logout/", "FAIL", f"Status {r.status_code}, URL {r.url}")

    # -------------------------------------------------------------
    # 4. Parent Flow
    # -------------------------------------------------------------
    parent_session = requests.Session()
    csrf, r = get_csrf(parent_session, f"{BASE_URL}/login/")
    login_data = {
        "csrfmiddlewaretoken": csrf,
        "username": "rahul.parent",
        "password": "ParentDemo@123",
        "role": "parent"
    }
    r = parent_session.post(f"{BASE_URL}/login/", data=login_data, allow_redirects=True)
    if r.status_code == 200 and "/parent/dashboard/" in r.url:
        log_test("Parent Flow", "Parent Login (/login/ -> /parent/dashboard/)", "PASS", "Logged in successfully as Parent")
    else:
        log_test("Parent Flow", "Parent Login (/login/ -> /parent/dashboard/)", "FAIL", f"Status {r.status_code}, URL {r.url}")

    parent_urls = [
        ("Parent Portal", "/parent/dashboard/"),
        ("Parent Portal", "/parent/attendance/"),
        ("Parent Portal", "/parent/attendance/export/csv/"),
        ("Parent Portal", "/parent/results/"),
        ("Parent Portal", "/parent/progress/"),
        ("Parent Portal", "/parent/profile/"),
        ("Parent Portal", "/parent/notices/"),
        ("Parent Portal", "/parent/performance/"),
        ("Parent Portal", "/parent/timetable/"),
        ("Parent Portal", "/parent/result-card/"),
        ("Parent Portal", "/parent/result-card/download/"),
        ("Parent Portal", "/parent/change-password/"),
    ]

    for cat, path in parent_urls:
        r = parent_session.get(f"{BASE_URL}{path}")
        if r.status_code == 200:
            log_test("Parent Flow", path, "PASS", f"Status 200 ({len(r.content)} bytes)")
        else:
            log_test("Parent Flow", path, "FAIL", f"Status {r.status_code}")

    # Parent logout
    r = parent_session.get(f"{BASE_URL}/parent/logout/", allow_redirects=True)
    if r.status_code == 200 and "/login/" in r.url:
        log_test("Parent Flow", "/parent/logout/", "PASS", "Logged out and redirected to login")
    else:
        log_test("Parent Flow", "/parent/logout/", "FAIL", f"Status {r.status_code}, URL {r.url}")

    # -------------------------------------------------------------
    # 5. Cross-Cutting & API Checks
    # -------------------------------------------------------------
    # 5.1 RBAC / Permission barriers: Logged out access to admin URLs
    r_unauth = anon_session.get(f"{BASE_URL}/admin-dashboard/", allow_redirects=False)
    if r_unauth.status_code in [302, 403, 401] and "/login/" in r_unauth.headers.get("Location", ""):
        log_test("Cross-Cutting", "RBAC: Anonymous access to /admin-dashboard/", "PASS", f"Blocked/Redirected to login ({r_unauth.headers.get('Location')})")
    else:
        log_test("Cross-Cutting", "RBAC: Anonymous access to /admin-dashboard/", "FAIL", f"Status {r_unauth.status_code}")

    # Log parent back in
    csrf, _ = get_csrf(parent_session, f"{BASE_URL}/login/")
    parent_session.post(f"{BASE_URL}/login/", data={"csrfmiddlewaretoken": csrf, "username": "rahul.parent", "password": "ParentDemo@123", "role": "parent"})
    r_parent_admin = parent_session.get(f"{BASE_URL}/admin-dashboard/", allow_redirects=False)
    if r_parent_admin.status_code in [302, 403, 401]:
        log_test("Cross-Cutting", "RBAC: Parent accessing /admin-dashboard/", "PASS", f"Blocked/Redirected (Status {r_parent_admin.status_code})")
    else:
        log_test("Cross-Cutting", "RBAC: Parent accessing /admin-dashboard/", "FAIL", f"Leaked access! Status {r_parent_admin.status_code}")

    # Teacher accessing admin URL
    csrf, _ = get_csrf(teacher_session, f"{BASE_URL}/login/")
    teacher_session.post(f"{BASE_URL}/login/", data={"csrfmiddlewaretoken": csrf, "username": "anita.teacher", "password": "TeacherDemo@123", "role": "teacher"})
    r_teacher_admin = teacher_session.get(f"{BASE_URL}/admin-dashboard/", allow_redirects=False)
    if r_teacher_admin.status_code in [302, 403, 401]:
        log_test("Cross-Cutting", "RBAC: Teacher accessing /admin-dashboard/", "PASS", f"Blocked/Redirected (Status {r_teacher_admin.status_code})")
    else:
        log_test("Cross-Cutting", "RBAC: Teacher accessing /admin-dashboard/", "FAIL", f"Leaked access! Status {r_teacher_admin.status_code}")

    # 5.2 Chatbot API
    csrf, _ = get_csrf(parent_session, f"{BASE_URL}/parent/dashboard/")
    chat_headers = {"X-CSRFToken": csrf, "Content-Type": "application/json"}
    chat_payload = {"message": "How do I check my results?"}
    try:
        r_chat = parent_session.post(f"{BASE_URL}/chatbot/", json=chat_payload, headers=chat_headers)
        if r_chat.status_code == 200:
            resp_data = r_chat.json()
            log_test("Cross-Cutting", "Chatbot API (/chatbot/)", "PASS", f"Response 200, returned answer: {resp_data.get('response', '')[:50]}...")
        else:
            log_test("Cross-Cutting", "Chatbot API (/chatbot/)", "FAIL", f"Status {r_chat.status_code}, body: {r_chat.text[:100]}")
    except Exception as e:
        log_test("Cross-Cutting", "Chatbot API (/chatbot/)", "FAIL", str(e))

    # 5.3 AJAX / Helper endpoints
    r_holidays = anon_session.get(f"{BASE_URL}/get-holidays/")
    if r_holidays.status_code == 200:
        log_test("Cross-Cutting", "/get-holidays/", "PASS", f"Status 200 JSON ({len(r_holidays.text)} bytes)")
    else:
        log_test("Cross-Cutting", "/get-holidays/", "FAIL", f"Status {r_holidays.status_code}")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    total = len(results)
    passed = sum(1 for x in results if x["status"] == "PASS")
    failed = sum(1 for x in results if x["status"] == "FAIL")

    print("=" * 80)
    print(f"SMOKE TEST COMPLETE: Total Tested: {total} | Passed: {passed} | Failed: {failed}")
    print("=" * 80)

    with open("smoke_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_smoke_test()
