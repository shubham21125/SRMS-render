import json
import logging
from django.http import JsonResponse
from django.conf import settings

from resultapp.models import Notice, Student, Class, Parent, Result, Attendance, ProgressReport
from .students import get_grade
from .parent import resolve_portal_viewer

logger = logging.getLogger(__name__)


def chatbot_api(request):
    """
    Smart chatbot endpoint powered by Google Gemini Flash (free tier).
    Builds rich school context from DB and sends it to Gemini for intelligent responses.
    Falls back to rule-based answers if API key is missing or quota exceeded.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
        conversation_history = body.get('history', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not user_message:
        return JsonResponse({'reply': "Please type a message so I can help you! 😊"})

    # ── Build School Context ───────────────────────────────
    context_lines = [
        "You are SRMS Assistant, a helpful chatbot for a Student Result Management System (SRMS).",
        "You help parents and students with their queries about results, attendance, progress reports, notices, and technical issues.",
        "Be concise, friendly, and professional. Use emojis sparingly to be warm.",
        "School name: SRMS College. Admin contact: admin@srms.edu | Phone: Available at school office.",
        "",
        "=== SCHOOL DATA ===",
    ]

    # Recent notices
    try:
        recent_notices = Notice.objects.all().order_by('-posting_date')[:3]
        if recent_notices:
            context_lines.append("Recent Notices:")
            for n in recent_notices:
                context_lines.append(f"  - [{n.posting_date.strftime('%d %b %Y')}] {n.title}: {n.detail[:120]}")
    except Exception:
        pass

    # Total stats
    try:
        context_lines.append(f"Total Students: {Student.objects.count()}")
        context_lines.append(f"Total Classes: {Class.objects.count()}")
    except Exception:
        pass

    # If parent is logged in — provide their child's real data
    is_parent = False
    parent_data_lines = []
    if request.user.is_authenticated and not request.user.is_superuser:
        try:
            parent = Parent.objects.select_related('student', 'student__student_class').get(user=request.user)
            student = parent.student
            is_parent = True

            parent_data_lines.append(f"\n=== LOGGED-IN PARENT DATA ===")
            parent_data_lines.append(f"Parent: {request.user.get_full_name()} ({getattr(parent, 'relationship', None) or 'Guardian'})")
            parent_data_lines.append(f"Child: {student.name} | Roll ID: {student.roll_id} | Class: {student.student_class}")

            # Results
            results = Result.objects.filter(student=student).select_related('subject')
            if results.exists():
                parent_data_lines.append("Results:")
                for r in results:
                    parent_data_lines.append(f"  - {r.subject.subject_name}: {r.total_obtained}/{r.total_max} ({r.subject_percentage:.1f}%) (Grade: {r.nep_grade})")
                total_obtained = sum(r.total_obtained for r in results)
                total_max      = sum(r.total_max for r in results)
                overall_pct    = (total_obtained / total_max * 100) if total_max > 0 else 0
                failed_any     = any(not r.is_subject_pass for r in results)
                overall_grade  = get_grade(overall_pct, failed_any)
                parent_data_lines.append(f"  Overall Average: {overall_pct:.1f}% | Overall Grade: {overall_grade}")
            else:
                parent_data_lines.append("Results: No results posted yet.")

            # Attendance
            from .students import compute_attendance_stats
            stats = compute_attendance_stats(student)
            if stats['total_days'] > 0:
                parent_data_lines.append(
                    f"Attendance: {stats['attended_days']}/{stats['total_days']} days attended "
                    f"({stats['percentage']:.1f}%) [Breakdown: Present: {stats['present_days']}, "
                    f"Late: {stats['late_days']}, Absent: {stats['absent_days']}]"
                )
            else:
                parent_data_lines.append("Attendance: No attendance records yet.")

            # Progress Reports
            progress = ProgressReport.objects.filter(student=student).order_by('-created_at').first()
            if progress:
                parent_data_lines.append(f"Latest Progress Report ({progress.term}): {progress.overall_percentage}% | Grade: {progress.grade}")
                if progress.teacher_remarks:
                    parent_data_lines.append(f"  Teacher Remarks: {progress.teacher_remarks[:150]}")

            context_lines.extend(parent_data_lines)
        except Parent.DoesNotExist:
            pass
        except Exception:
            pass

    context_lines.append("\n=== HOW TO USE SRMS ===")
    context_lines.append("- To download/print result: Go to Parent Portal > Results > click 'Print' or use Ctrl+P on result page.")
    context_lines.append("- Login issues: Use the 'Forgot Password' link on login page, or contact admin to reset password.")
    context_lines.append("- To view attendance: Parent Portal > Attendance.")
    context_lines.append("- To view notices: Homepage shows all notices. Click any notice for details.")
    context_lines.append("- If result not showing: Contact admin to verify result has been posted for your child.")
    context_lines.append("- PDF result: On the result page, press Ctrl+P (Windows) or Cmd+P (Mac) and select 'Save as PDF'.")

    system_context = "\n".join(context_lines)

    # ── Try Gemini API ─────────────────────────────────────
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
    reply = None

    if gemini_api_key:
        try:
            from google import genai as google_genai
            from google.genai import types as genai_types

            client = google_genai.Client(api_key=gemini_api_key)

            # Build chat history for multi-turn context
            contents = []
            for item in conversation_history[-6:]:   # last 3 pairs
                role = 'user' if item.get('role') == 'user' else 'model'
                contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=item.get('content', ''))]))

            # Add current user message
            contents.append(genai_types.Content(role='user', parts=[genai_types.Part(text=user_message)]))

            response = client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_context,
                    max_output_tokens=300,
                    temperature=0.7,
                ),
            )
            reply = response.text.strip()
        except Exception:
            logger.exception("Gemini API call failed, falling back to rule-based system")
            reply = None

    # ── Rule-Based Fallback ────────────────────────────────
    if not reply:
        msg_lower = user_message.lower()

        if any(w in msg_lower for w in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'namaste']):
            name = (request.user.get_full_name().strip() or request.user.username) if request.user.is_authenticated else "there"
            reply = f"Hello {name}! 👋 I'm SRMS Assistant. I can help you with results, attendance, notices, PDF downloads, login issues, and more. What would you like to know?"

        elif any(w in msg_lower for w in ['pdf', 'download', 'print', 'save']):
            reply = "📄 **To download/save your result as PDF:**\n1. Go to **Parent Portal → Results**\n2. On the result page, press **Ctrl+P** (Windows) or **Cmd+P** (Mac)\n3. In the print dialog, choose **'Save as PDF'** as the printer\n4. Click Save\n\nIf you don't see results, contact admin to ensure marks have been posted."

        elif any(w in msg_lower for w in ['login', 'password', 'forgot', 'reset', 'sign in', 'cant login', "can't login"]):
            reply = "🔐 **Login Issues — Try these steps:**\n1. Click **'Forgot Password'** on the login page\n2. Enter your registered email to reset\n3. Check your spam folder for the reset email\n4. If still stuck, contact your school admin to reset your account\n\nMake sure you're using the **Parent Portal** login, not the Admin login."

        elif any(w in msg_lower for w in ['result', 'mark', 'score', 'grade', 'exam']):
            if is_parent and parent_data_lines:
                reply = "📊 Here's your child's result summary:\n" + "\n".join(
                    [l for l in parent_data_lines if 'Result' in l or 'Average' in l or 'Grade' in l]
                )
                reply += "\n\nFor detailed results, go to **Parent Portal → Results**."
            else:
                reply = "📊 To view results, log in to the **Parent Portal** and go to the **Results** section. If results aren't visible, they may not have been posted yet — contact your admin."

        elif any(w in msg_lower for w in ['attendance', 'present', 'absent', 'late']):
            if is_parent and parent_data_lines:
                att_line = next((l for l in parent_data_lines if 'Attendance' in l), None)
                reply = f"📅 {att_line}\n\nFor detailed attendance, go to **Parent Portal → Attendance**." if att_line else "Go to **Parent Portal → Attendance** to view detailed records."
            else:
                reply = "📅 Attendance records are available in the **Parent Portal → Attendance** section after logging in."

        elif any(w in msg_lower for w in ['notice', 'announcement', 'news', 'update']):
            try:
                notices = Notice.objects.all().order_by('-posting_date')[:3]
                if notices:
                    reply = "📢 **Latest Notices:**\n" + "\n".join([f"• **{n.title}** ({n.posting_date.strftime('%d %b')})" for n in notices])
                    reply += "\n\nView full notices on the **Homepage**."
                else:
                    reply = "No notices posted yet. Check back soon!"
            except Exception:
                reply = "Please check the homepage for the latest notices."

        elif any(w in msg_lower for w in ['progress', 'report', 'performance', 'remark']):
            if is_parent and parent_data_lines:
                prog_lines = [l for l in parent_data_lines if 'Progress' in l or 'Remark' in l]
                reply = "📈 " + "\n".join(prog_lines) if prog_lines else "No progress report available yet."
            else:
                reply = "📈 Progress reports are in **Parent Portal → Progress Reports**."

        elif any(w in msg_lower for w in ['contact', 'phone', 'email', 'admin', 'support', 'help']):
            reply = "📞 **Contact SRMS Admin:**\n• Email: admin@srms.edu\n• Visit the school office during working hours (Mon–Sat, 9 AM – 5 PM)\n• For urgent issues, speak to the class teacher directly."

        elif any(w in msg_lower for w in ['thank', 'thanks', 'bye', 'goodbye']):
            reply = "You're welcome! 😊 If you have any more questions, feel free to ask. Have a great day! 🌟"

        else:
            reply = (
                "I'm not sure I understood that. Here are things I can help with:\n\n"
                "• 📊 **View Results** — Ask 'show my results'\n"
                "• 📅 **Attendance** — Ask 'show attendance'\n"
                "• 📄 **Download PDF** — Ask 'how to download result PDF'\n"
                "• 🔐 **Login Issues** — Ask 'I can't login'\n"
                "• 📢 **Notices** — Ask 'show latest notices'\n"
                "• 📞 **Contact Admin** — Ask 'how to contact admin'\n\n"
                "You can also type your question in your own words!"
            )

    return JsonResponse({'reply': reply, 'is_parent': is_parent})
