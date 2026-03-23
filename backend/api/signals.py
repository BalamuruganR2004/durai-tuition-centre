from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Attendance, Mark, Fee, Notification
from .tasks import (
    send_absence_notification,
    send_result_notification,
    send_fee_reminder,
)


@receiver(post_save, sender=Attendance)
def attendance_notification(sender, instance, created, **kwargs):