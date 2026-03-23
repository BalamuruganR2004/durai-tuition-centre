from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Student, Parent, Teacher, Class, Subject,
    Attendance, Exam, Mark, Note, Homework, Fee, Payment,
    Timetable, WhatsAppLog, Notification,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role & Contact", {"fields": ("role", "phone", "whatsapp_number", "profile_picture")}),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user", "admission_number", "roll_number", "current_class", "is_active")
    list_filter = ("current_class", "is_active", "gender")
    search_fields = ("user__first_name", "user__last_name", "admission_number")


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "specialization", "is_active")
    list_filter = ("is_active",)
    search_fields = ("user__first_name", "user__last_name", "employee_id")


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("user", "occupation")
    search_fields = ("user__first_name", "user__last_name")


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "grade", "section", "academic_year", "class_teacher")
    list_filter = ("grade", "academic_year")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "class_ref", "date", "status", "notification_sent")
    list_filter = ("status", "date", "class_ref")
    date_hierarchy = "date"


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "subject", "marks_obtained", "total_marks")
    list_filter = ("exam", "subject")


@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ("student", "fee_type", "amount", "amount_paid", "due_date")
    list_filter = ("fee_type", "academic_year")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")


# Simple registrations
admin.site.register(Subject)
admin.site.register(Exam)
admin.site.register(Note)
admin.site.register(Homework)
admin.site.register(Payment)
admin.site.register(Timetable)
admin.site.register(WhatsAppLog)

admin.site.site_header = "Durai Tuition Centre — Admin"
admin.site.site_title = "Durai Admin"
admin.site.index_title = "Management Dashboard"