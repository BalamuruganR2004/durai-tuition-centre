import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "durai_backend.settings")

app = Celery("durai_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ── Periodic task schedule ────────────────────
app.conf.beat_schedule = {
    # Daily attendance alert at 9 PM
    "daily-attendance-alert": {
        "task": "api.tasks.daily_attendance_alert",
        "schedule": crontab(hour=21, minute=0),
    },
    # Generate monthly fee records on 1st of every month
    "generate-monthly-fees": {
        "task": "api.tasks.generate_monthly_fee_records",
        "schedule": crontab(day_of_month=1, hour=0, minute=5),
    },
    # Send pending fee reminders every Monday 10 AM
    "weekly-fee-reminders": {
        "task": "api.tasks.send_bulk_fee_reminders",
        "schedule": crontab(day_of_week=1, hour=10, minute=0),
    },
    # AI risk re-assessment every Sunday midnight
    "ai-risk-scan": {
        "task": "api.tasks.ai_risk_assessment_all_students",
        "schedule": crontab(day_of_week=0, hour=0, minute=30),
    },
}