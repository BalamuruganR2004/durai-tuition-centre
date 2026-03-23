"""Celery background tasks - WhatsApp notifications, fee reminders, AI risk scoring."""
import logging, requests
from datetime import date
from celery import shared_task
from django.conf import settings

logger = logging.getLogger('api')

def send_whatsapp_message(phone: str, message: str, msg_type: str = 'general') -> bool:
    try:
        url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        resp = requests.post(url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product":"whatsapp","to":phone,"type":"text","text":{"body":message}},
            timeout=10)
        resp.raise_for_status()
        from .models import WhatsAppLog
        WhatsAppLog.objects.create(phone_number=phone, message=message, message_type=msg_type, status='sent')
        return True
    except Exception as e:
        logger.error(f"WhatsApp failed to {phone}: {e}")
        return False

@shared_task(bind=True, max_retries=3)
def send_absence_notification(self, student_id: int, date_str: str):
    try:
        from .models import Student
        student = Student.objects.select_related('user','parent__user').get(pk=student_id)
        if not student.parent: return
        phone = student.parent.user.whatsapp_number or student.parent.user.phone
        if not phone: return
        msg = (f"Dear {student.parent.user.get_full_name()},\n\n"
               f"Your child {student.user.get_full_name()} was absent from "
               f"Durai Tuition Centre today ({date_str}).\n\n"
               f"Please ensure regular attendance.\n\n- Durai Tuition Centre")
        send_whatsapp_message(phone, msg, 'absence')
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_result_notification(self, mark_id: int):
    try:
        from .models import Mark
        mark = Mark.objects.select_related('student__user','student__parent__user','subject','exam').get(pk=mark_id)
        if not mark.student.parent: return
        phone = mark.student.parent.user.whatsapp_number or mark.student.parent.user.phone
        if not phone: return
        msg = (f"Dear {mark.student.parent.user.get_full_name()},\n\n"
               f"Result for {mark.student.user.get_full_name()}:\n"
               f"{mark.subject.name}: {mark.marks_obtained}/{mark.total_marks} (Grade: {mark.grade})\n"
               f"Exam: {mark.exam.name}\n\n- Durai Tuition Centre")
        send_whatsapp_message(phone, msg, 'result')
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_fee_reminder(self, fee_id: int):
    try:
        from .models import Fee
        fee = Fee.objects.select_related('student__user','student__parent__user').get(pk=fee_id)
        if not fee.student.parent: return
        phone = fee.student.parent.user.whatsapp_number or fee.student.parent.user.phone
        if not phone: return
        msg = (f"Dear {fee.student.parent.user.get_full_name()},\n\n"
               f"Fee Reminder for {fee.student.user.get_full_name()}:\n"
               f"Amount Due: ₹{fee.balance}\nDue Date: {fee.due_date}\n\n"
               f"Please pay at the earliest.\n\n- Durai Tuition Centre")
        send_whatsapp_message(phone, msg, 'fee')
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@shared_task
def send_bulk_fee_reminders():
    from .models import Fee
    from django.db.models import F
    pending = Fee.objects.filter(amount_paid__lt=F('amount'))
    for fee in pending:
        send_fee_reminder.delay(fee.id)

@shared_task
def daily_attendance_alert():
    from .models import Student, Attendance, Notification
    from django.db.models import Count, Q
    for student in Student.objects.filter(is_active=True).select_related('user','parent__user'):
        total = Attendance.objects.filter(student=student).count()
        if not total: continue
        present = Attendance.objects.filter(student=student, status='P').count()
        pct = present / total * 100
        if pct < 75 and student.parent:
            phone = student.parent.user.whatsapp_number or student.parent.user.phone
            if phone:
                msg = (f"⚠️ Attendance Alert!\n{student.user.get_full_name()}'s attendance "
                       f"is {pct:.1f}% — below the required 75%.\n\n- Durai Tuition Centre")
                send_whatsapp_message(phone, msg, 'attendance_warning')

@shared_task
def generate_monthly_fee_records():
    from .models import Student, Fee, FeeStructure
    import datetime
    today = date.today()
    for student in Student.objects.filter(is_active=True):
        Fee.objects.get_or_create(
            student=student,
            month=today.month,
            academic_year=f"{today.year}-{str(today.year+1)[2:]}",
            defaults={'amount': 3500, 'due_date': today.replace(day=10)}
        )
