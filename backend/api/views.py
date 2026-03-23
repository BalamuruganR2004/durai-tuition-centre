"""
=============================================================================
DURAI TUITION CENTRE — api/views.py  (COMPLETE)
=============================================================================
All ViewSets, APIViews, Dashboard views, Report views, AI views, Webhook.
=============================================================================
"""

import io
import json
import logging
import requests
from datetime import date, timedelta
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django_filters.rest_framework import DjangoFilterBackend
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable,
)

from .models import (
    User, Student, Parent, Teacher, Class, Subject,
    Attendance, Exam, Mark, Note, Homework, HomeworkSubmission,
    Fee, Payment, Timetable, WhatsAppLog, SMSLog, AILog, Notification,
)
from .serializers import (
    LoginSerializer, UserSerializer, ChangePasswordSerializer,
    StudentSerializer, ParentSerializer, TeacherSerializer,
    ClassSerializer, SubjectSerializer,
    AttendanceSerializer, BulkAttendanceSerializer,
    ExamSerializer, MarkSerializer,
    NoteSerializer, HomeworkSerializer, HomeworkSubmissionSerializer,
    FeeSerializer, PaymentSerializer,
    TimetableSerializer, NotificationSerializer,
    WhatsAppLogSerializer, SMSLogSerializer,
)
from .permissions import (
    IsAdmin, IsAdminOrTeacher, IsAdminOrReadOnly, OwnDataOnly,
)
from .tasks import (
    send_absence_notification, send_fee_reminder,
    send_result_notification, send_bulk_fee_reminders,
)

logger = logging.getLogger("api")
User = get_user_model()


# ══════════════════════════════════════════════════════════════════════════════
# AUTH VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class LogoutView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
        except Exception:
            pass
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password changed."})


# ══════════════════════════════════════════════════════════════════════════════
# STUDENT VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["current_class", "is_active", "gender"]
    search_fields = ["user__first_name", "user__last_name", "admission_number"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Student.objects.select_related("user", "parent", "current_class").all()
        if user.role == "teacher":
            # Teacher sees students in their classes
            teacher = Teacher.objects.get(user=user)
            class_ids = teacher.classes.values_list("id", flat=True)
            return Student.objects.filter(current_class__id__in=class_ids)
        if user.role == "student":
            return Student.objects.filter(user=user)
        if user.role == "parent":
            parent = Parent.objects.get(user=user)
            return Student.objects.filter(parent=parent)
        return Student.objects.none()

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["get"])
    def profile(self, request, pk=None):
        """Full student profile with attendance, marks, fees summary."""
        student = self.get_object()
        data = StudentSerializer(student).data

        # Attendance summary
        att_total = Attendance.objects.filter(student=student).count()
        att_present = Attendance.objects.filter(student=student, status="P").count()
        data["attendance"] = {
            "total": att_total,
            "present": att_present,
            "absent": att_total - att_present,
            "percentage": round((att_present / att_total * 100), 1) if att_total else 100.0,
        }

        # Recent marks
        marks = Mark.objects.filter(student=student).order_by("-created_at")[:10]
        data["recent_marks"] = MarkSerializer(marks, many=True).data

        # Fee status
        fees = Fee.objects.filter(student=student)
        data["fees"] = {
            "total_due": fees.aggregate(Sum("amount"))["amount__sum"] or 0,
            "total_paid": fees.aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0,
            "pending_count": fees.filter(amount_paid__lt=Q("amount")).count(),
        }

        return Response(data)


# ══════════════════════════════════════════════════════════════════════════════
# PARENT VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class ParentViewSet(viewsets.ModelViewSet):
    serializer_class = ParentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["user__first_name", "user__last_name", "user__phone"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Parent.objects.select_related("user").all()
        if user.role == "parent":
            return Parent.objects.filter(user=user)
        return Parent.objects.none()

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


# ══════════════════════════════════════════════════════════════════════════════
# TEACHER VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["user__first_name", "user__last_name", "specialization"]

    def get_queryset(self):
        return Teacher.objects.select_related("user").filter(is_active=True)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


# ══════════════════════════════════════════════════════════════════════════════
# CLASS VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.prefetch_related("subjects").all()
    serializer_class = ClassSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["grade", "academic_year"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        cls = self.get_object()
        students = Student.objects.filter(current_class=cls)
        return Response(StudentSerializer(students, many=True).data)

    @action(detail=True, methods=["get"])
    def timetable(self, request, pk=None):
        cls = self.get_object()
        timetable = Timetable.objects.filter(class_ref=cls).order_by("day_of_week", "start_time")
        return Response(TimetableSerializer(timetable, many=True).data)


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


# ══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["student", "class_ref", "date", "status"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Attendance.objects.all()
        if user.role == "teacher":
            teacher = Teacher.objects.get(user=user)
            class_ids = teacher.classes.values_list("id", flat=True)
            return Attendance.objects.filter(class_ref__id__in=class_ids)
        if user.role == "student":
            student = Student.objects.get(user=user)
            return Attendance.objects.filter(student=student)
        if user.role == "parent":
            parent = Parent.objects.get(user=user)
            return Attendance.objects.filter(student__parent=parent)
        return Attendance.objects.none()

    def get_permissions(self):
        if self.action in ("bulk_mark",):
            return [IsAdminOrTeacher()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["post"])
    def bulk_mark(self, request):
        """Mark attendance for entire class at once."""
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        cls = Class.objects.get(pk=data["class_id"])
        att_date = data["date"]
        records = data["records"]

        created_count = 0
        absent_students = []

        for rec in records:
            obj, created = Attendance.objects.update_or_create(
                student_id=rec["student_id"],
                class_ref=cls,
                date=att_date,
                defaults={
                    "status": rec["status"],
                    "remarks": rec.get("remarks", ""),
                    "subject_id": data.get("subject_id"),
                },
            )
            if created:
                created_count += 1
            if rec["status"] == "A":
                absent_students.append(rec["student_id"])

        # Trigger async notifications for absent students
        for student_id in absent_students:
            send_absence_notification.delay(student_id, str(att_date))

        return Response({
            "detail": f"Attendance marked for {len(records)} students.",
            "absent": len(absent_students),
        })

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Attendance summary per student for a class/date range."""
        class_id = request.query_params.get("class_id")
        start = request.query_params.get("start", str(date.today() - timedelta(days=30)))
        end = request.query_params.get("end", str(date.today()))

        qs = Attendance.objects.filter(date__range=[start, end])
        if class_id:
            qs = qs.filter(class_ref_id=class_id)

        summary = qs.values("student__id", "student__user__first_name",
                            "student__user__last_name").annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status="P")),
            absent=Count("id", filter=Q(status="A")),
            late=Count("id", filter=Q(status="L")),
        )

        result = []
        for row in summary:
            total = row["total"]
            present = row["present"]
            result.append({
                "student_id": row["student__id"],
                "name": f"{row['student__user__first_name']} {row['student__user__last_name']}",
                "total": total,
                "present": present,
                "absent": row["absent"],
                "late": row["late"],
                "percentage": round(present / total * 100, 1) if total else 100.0,
            })

        return Response(result)


# ══════════════════════════════════════════════════════════════════════════════
# EXAM & MARKS VIEWSETS
# ══════════════════════════════════════════════════════════════════════════════

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["class_ref", "exam_type", "academic_year"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminOrTeacher()]
        return [IsAuthenticated()]


class MarkViewSet(viewsets.ModelViewSet):
    serializer_class = MarkSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["student", "exam", "subject"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("admin", "teacher"):
            return Mark.objects.all()
        if user.role == "student":
            student = Student.objects.get(user=user)
            return Mark.objects.filter(student=student)
        if user.role == "parent":
            parent = Parent.objects.get(user=user)
            return Mark.objects.filter(student__parent=parent)
        return Mark.objects.none()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAdminOrTeacher()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def progress(self, request):
        """Track student progress across exam types."""
        student_id = request.query_params.get("student_id")
        subject_id = request.query_params.get("subject_id")

        if not student_id:
            return Response({"error": "student_id required"}, status=400)

        qs = Mark.objects.filter(student_id=student_id).order_by("exam__date")
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        # Group by subject
        by_subject = defaultdict(list)
        for m in qs:
            by_subject[m.subject.name].append({
                "exam": m.exam.name,
                "exam_type": m.exam.exam_type,
                "date": str(m.exam.date),
                "marks_obtained": m.marks_obtained,
                "total_marks": m.total_marks,
                "percentage": m.percentage,
                "grade": m.grade,
            })

        result = []
        for subject, exams in by_subject.items():
            if len(exams) >= 2:
                trend = "improving" if exams[-1]["percentage"] > exams[-2]["percentage"] else "declining"
            else:
                trend = "stable"
            result.append({
                "subject": subject,
                "exams": exams,
                "trend": trend,
                "average": round(sum(e["percentage"] for e in exams) / len(exams), 1),
            })

        return Response(result)

    @action(detail=False, methods=["post"])
    def bulk_enter(self, request):
        """Enter marks for multiple students at once."""
        records = request.data.get("records", [])
        created = []
        for rec in records:
            obj, _ = Mark.objects.update_or_create(
                student_id=rec["student_id"],
                exam_id=rec["exam_id"],
                subject_id=rec["subject_id"],
                defaults={
                    "marks_obtained": rec["marks_obtained"],
                    "total_marks": rec["total_marks"],
                    "remarks": rec.get("remarks", ""),
                },
            )
            created.append(obj.id)
        return Response({"detail": f"{len(created)} marks saved."})


# ══════════════════════════════════════════════════════════════════════════════
# NOTES & HOMEWORK VIEWSETS
# ══════════════════════════════════════════════════════════════════════════════

class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["class_ref", "subject", "is_question_paper"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("admin", "teacher"):
            return Note.objects.all()
        if user.role == "student":
            student = Student.objects.get(user=user)
            return Note.objects.filter(
                class_ref=student.current_class, is_active=True
            )
        if user.role == "parent":
            parent = Parent.objects.get(user=user)
            children_classes = parent.children.values_list("current_class", flat=True)
            return Note.objects.filter(class_ref__in=children_classes, is_active=True)
        return Note.objects.none()

    def perform_create(self, serializer):
        teacher = Teacher.objects.get(user=self.request.user)
        serializer.save(teacher=teacher)

    @action(detail=True, methods=["post"])
    def download(self, request, pk=None):
        note = self.get_object()
        note.download_count += 1
        note.save()
        return Response({"url": request.build_absolute_uri(note.file.url)})


class HomeworkViewSet(viewsets.ModelViewSet):
    serializer_class = HomeworkSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["class_ref", "subject"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("admin", "teacher"):
            return Homework.objects.all()
        if user.role == "student":
            student = Student.objects.get(user=user)
            return Homework.objects.filter(class_ref=student.current_class)
        if user.role == "parent":
            parent = Parent.objects.get(user=user)
            children_classes = parent.children.values_list("current_class", flat=True)
            return Homework.objects.filter(class_ref__in=children_classes)
        return Homework.objects.none()

    def perform_create(self, serializer):
        teacher = Teacher.objects.get(user=self.request.user)
        serializer.save(teacher=teacher)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        homework = self.get_object()
        student = Student.objects.get(user=request.user)
        sub, created = HomeworkSubmission.objects.update_or_create(
            homework=homework,
            student=student,
            defaults={
                "file": request.FILES.get("file"),
                "remarks": request.data.get("remarks", ""),
                "is_submitted": True,
            },
        )
        return Response(HomeworkSubmissionSerializer(sub).data)


# ══════════════════════════════════════════════════════════════════════════════
# FEES VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class FeeViewSet(viewsets.ModelViewSet):
    serializer_class = FeeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["student", "fee_type", "academic_year"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Fee.objects.all()
        if user.role == "student":
            student = Student.objects.get(user=user)
            return Fee.objects.filter(student=student)
        if user.role == "parent":
            parent = Parent.objects.get(user=user)
            return Fee.objects.filter(student__parent=parent)
        return Fee.objects.none()

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        fee = self.get_object()
        amount = float(request.data.get("amount", 0))
        payment_mode = request.data.get("payment_mode", "cash")
        reference = request.data.get("reference", "")

        fee.amount_paid += amount
        if fee.amount_paid > fee.amount:
            fee.amount_paid = fee.amount
        fee.save()

        # Create payment record
        payment = Payment.objects.create(
            fee=fee,
            amount=amount,
            payment_mode=payment_mode,
            reference_number=reference,
        )

        return Response({
            "detail": "Payment recorded.",
            "receipt_number": fee.receipt_number,
            "balance": fee.balance,
            "payment_id": payment.id,
        })

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        fee = self.get_object()
        return Response({
            "receipt_number": fee.receipt_number,
            "student": fee.student.user.get_full_name(),
            "class": str(fee.student.current_class),
            "fee_type": fee.get_fee_type_display(),
            "amount": fee.amount,
            "amount_paid": fee.amount_paid,
            "balance": fee.balance,
            "academic_year": fee.academic_year,
            "date": str(date.today()),
        })

    @action(detail=False, methods=["post"])
    def send_reminders(self, request):
        """Send WhatsApp reminders for all pending fees."""
        send_bulk_fee_reminders.delay()
        return Response({"detail": "Fee reminders queued."})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        fees = self.get_queryset()
        return Response({
            "total_due": fees.aggregate(Sum("amount"))["amount__sum"] or 0,
            "total_collected": fees.aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0,
            "pending_count": fees.filter(amount_paid__lt=fees.values("amount")).count(),
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Payment.objects.all()
        return Payment.objects.none()


# ══════════════════════════════════════════════════════════════════════════════
# TIMETABLE VIEWSET
# ══════════════════════════════════════════════════════════════════════════════

class TimetableViewSet(viewsets.ModelViewSet):
    queryset = Timetable.objects.all()
    serializer_class = TimetableSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["class_ref", "day_of_week", "teacher"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS & LOGS
# ══════════════════════════════════════════════════════════════════════════════

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})


class WhatsAppLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WhatsAppLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "message_type"]

    def get_queryset(self):
        if self.request.user.role == "admin":
            return WhatsAppLog.objects.all().order_by("-sent_at")
        return WhatsAppLog.objects.none()


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class AdminDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        # Student stats
        total_students = Student.objects.filter(is_active=True).count()
        new_this_month = Student.objects.filter(created_at__date__gte=thirty_days_ago).count()

        # Attendance today
        att_today = Attendance.objects.filter(date=today)
        att_present = att_today.filter(status="P").count()
        att_absent = att_today.filter(status="A").count()

        # Fee collection
        total_fees = Fee.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        collected = Fee.objects.aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0
        pending = total_fees - collected

        # Weak students (attendance < 75% OR avg marks < 40%)
        weak_students = []
        for student in Student.objects.filter(is_active=True).select_related("user"):
            att_total = Attendance.objects.filter(student=student).count()
            att_pct = (
                Attendance.objects.filter(student=student, status="P").count() / att_total * 100
                if att_total else 100
            )
            marks = Mark.objects.filter(student=student)
            avg_marks = (
                sum(m.percentage for m in marks) / marks.count()
                if marks.exists() else None
            )
            if att_pct < 75 or (avg_marks is not None and avg_marks < 40):
                weak_students.append({
                    "id": student.id,
                    "name": student.user.get_full_name(),
                    "attendance_pct": round(att_pct, 1),
                    "avg_marks": round(avg_marks, 1) if avg_marks else None,
                })

        return Response({
            "students": {"total": total_students, "new_this_month": new_this_month},
            "teachers": {"total": Teacher.objects.filter(is_active=True).count()},
            "classes": {"total": Class.objects.count()},
            "attendance_today": {
                "present": att_present,
                "absent": att_absent,
                "total": att_present + att_absent,
            },
            "fees": {
                "total": total_fees,
                "collected": collected,
                "pending": pending,
                "collection_rate": round(collected / total_fees * 100, 1) if total_fees else 0,
            },
            "weak_students": weak_students[:10],
            "recent_notifications": NotificationSerializer(
                Notification.objects.order_by("-created_at")[:5], many=True
            ).data,
        })


class TeacherDashboardView(APIView):
    def get(self, request):
        teacher = Teacher.objects.get(user=request.user)
        today = date.today()
        my_classes = teacher.classes.all()
        student_ids = Student.objects.filter(current_class__in=my_classes).values_list("id", flat=True)

        # Today's attendance status
        att_marked = Attendance.objects.filter(
            class_ref__in=my_classes, date=today
        ).values("class_ref").distinct().count()

        # Pending homework to grade
        pending_hw = Homework.objects.filter(teacher=teacher, due_date__lt=today).count()

        # Today's timetable
        today_tt = Timetable.objects.filter(
            teacher=teacher,
            day_of_week=today.strftime("%A")
        ).order_by("start_time")

        return Response({
            "my_classes": ClassSerializer(my_classes, many=True).data,
            "total_students": len(student_ids),
            "attendance_marked_today": att_marked,
            "pending_homework": pending_hw,
            "today_timetable": TimetableSerializer(today_tt, many=True).data,
            "recent_activity": [],
        })


class StudentDashboardView(APIView):
    def get(self, request):
        student = Student.objects.get(user=request.user)
        today = date.today()

        # Attendance
        att_total = Attendance.objects.filter(student=student).count()
        att_present = Attendance.objects.filter(student=student, status="P").count()
        att_pct = round(att_present / att_total * 100, 1) if att_total else 100.0

        # Latest marks
        latest_marks = Mark.objects.filter(student=student).order_by("-created_at")[:5]

        # Pending homework
        pending_hw = Homework.objects.filter(
            class_ref=student.current_class,
            due_date__gte=today,
        ).exclude(submissions__student=student)

        # Fee status
        fee_pending = Fee.objects.filter(
            student=student,
        ).aggregate(
            pending=Sum("amount") - Sum("amount_paid")
        )["pending"] or 0

        # Today's timetable
        today_tt = Timetable.objects.filter(
            class_ref=student.current_class,
            day_of_week=today.strftime("%A"),
        ).order_by("start_time")

        return Response({
            "student": StudentSerializer(student).data,
            "attendance": {"percentage": att_pct, "present": att_present, "total": att_total},
            "latest_marks": MarkSerializer(latest_marks, many=True).data,
            "pending_homework": HomeworkSerializer(pending_hw, many=True).data,
            "fee_pending": fee_pending,
            "today_timetable": TimetableSerializer(today_tt, many=True).data,
            "notifications": NotificationSerializer(
                Notification.objects.filter(user=request.user, is_read=False)[:5], many=True
            ).data,
        })


class ParentDashboardView(APIView):
    def get(self, request):
        parent = Parent.objects.get(user=request.user)
        children = Student.objects.filter(parent=parent)

        children_data = []
        for child in children:
            att_total = Attendance.objects.filter(student=child).count()
            att_present = Attendance.objects.filter(student=child, status="P").count()
            att_pct = round(att_present / att_total * 100, 1) if att_total else 100.0

            latest_mark = Mark.objects.filter(student=child).order_by("-created_at").first()
            fee_pending = Fee.objects.filter(student=child).aggregate(
                p=Sum("amount") - Sum("amount_paid")
            )["p"] or 0

            children_data.append({
                "student": StudentSerializer(child).data,
                "attendance_pct": att_pct,
                "latest_mark": MarkSerializer(latest_mark).data if latest_mark else None,
                "fee_pending": fee_pending,
            })

        return Response({
            "children": children_data,
            "notifications": NotificationSerializer(
                Notification.objects.filter(user=request.user, is_read=False)[:10], many=True
            ).data,
        })


# ══════════════════════════════════════════════════════════════════════════════
# AI VIEWS
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPTS = {
    "admin": """You are an AI assistant for Durai Tuition Centre admin. 
You have access to student, teacher, attendance, marks, and fee data.
Help with reports, analytics, weak student detection, and management decisions.
Always be concise and data-driven.""",
    "teacher": """You are an AI teaching assistant for Durai Tuition Centre.
Help teachers with lesson planning, student assessment strategies, and identifying struggling students.
Provide pedagogical advice and curriculum support.""",
    "student": """You are a friendly AI study assistant for Durai Tuition Centre students.
Help with subject doubts, study planning, exam preparation, and time management.
Be encouraging and explain concepts clearly.""",
    "parent": """You are an AI assistant for parents at Durai Tuition Centre.
Help parents understand their child's progress, attendance, and fees.
Provide guidance on supporting their child's education.""",
}


class AIChatView(APIView):
    def post(self, request):
        message = request.data.get("message", "")
        history = request.data.get("history", [])

        if not message:
            return Response({"error": "Message is required."}, status=400)

        user_role = request.user.role
        system_prompt = SYSTEM_PROMPTS.get(user_role, SYSTEM_PROMPTS["student"])

        # Build message history
        messages = []
        for h in history[-10:]:  # Last 10 turns for context
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": messages,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            ai_reply = data["content"][0]["text"]

            # Log AI interaction
            AILog.objects.create(
                user=request.user,
                query=message,
                response=ai_reply,
                model="claude-sonnet-4-20250514",
                tokens_used=data.get("usage", {}).get("output_tokens", 0),
            )

            return Response({"reply": ai_reply})

        except requests.RequestException as e:
            logger.error(f"AI chat error: {e}")
            return Response({"error": "AI service unavailable."}, status=503)


class AIStudyPlanView(APIView):
    def post(self, request):
        """Generate personalised study plan for a student."""
        student_id = request.data.get("student_id") or (
            Student.objects.get(user=request.user).id
            if request.user.role == "student" else None
        )
        if not student_id:
            return Response({"error": "student_id required."}, status=400)

        student = Student.objects.select_related("user", "current_class").get(pk=student_id)
        marks = Mark.objects.filter(student=student).select_related("subject", "exam")
        exams_upcoming = Exam.objects.filter(
            class_ref=student.current_class,
            date__gte=date.today(),
        ).order_by("date")[:5]

        # Build context
        marks_summary = "\n".join([
            f"- {m.subject.name}: {m.marks_obtained}/{m.total_marks} ({m.exam.name})"
            for m in marks.order_by("-created_at")[:10]
        ])
        upcoming_exams = "\n".join([
            f"- {e.name} on {e.date}" for e in exams_upcoming
        ])

        prompt = f"""
Create a personalised weekly study plan for {student.user.get_full_name()} in {student.current_class}.

Recent exam marks:
{marks_summary or "No marks available yet."}

Upcoming exams:
{upcoming_exams or "No upcoming exams scheduled."}

Generate a 7-day study plan with:
1. Daily time allocation per subject (focus more on weak subjects)
2. Specific topics to cover each day
3. Revision strategies
4. Practice test recommendations
Format as structured, actionable plan.
"""

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=45,
            )
            resp.raise_for_status()
            plan = resp.json()["content"][0]["text"]
            return Response({"plan": plan, "student": student.user.get_full_name()})

        except requests.RequestException:
            return Response({"error": "AI service unavailable."}, status=503)


class AIAnalyticsView(APIView):
    permission_classes = [IsAdminOrTeacher]

    def get(self, request):
        """Return at-risk students with AI risk scoring."""
        class_id = request.query_params.get("class_id")
        qs = Student.objects.filter(is_active=True).select_related("user", "current_class")
        if class_id:
            qs = qs.filter(current_class_id=class_id)

        at_risk = []
        for student in qs:
            risk_score = 0
            reasons = []

            att_total = Attendance.objects.filter(student=student).count()
            if att_total:
                att_pct = Attendance.objects.filter(student=student, status="P").count() / att_total * 100
                if att_pct < 75:
                    risk_score += 40
                    reasons.append(f"Low attendance: {att_pct:.1f}%")
                elif att_pct < 85:
                    risk_score += 20
                    reasons.append(f"Below-average attendance: {att_pct:.1f}%")
            else:
                att_pct = 100

            marks = Mark.objects.filter(student=student)
            if marks.exists():
                avg_marks = sum(m.percentage for m in marks) / marks.count()
                if avg_marks < 35:
                    risk_score += 50
                    reasons.append(f"Very low marks: {avg_marks:.1f}%")
                elif avg_marks < 50:
                    risk_score += 30
                    reasons.append(f"Below-average marks: {avg_marks:.1f}%")
            else:
                avg_marks = None

            fee_pending = Fee.objects.filter(student=student).aggregate(
                p=Sum("amount") - Sum("amount_paid")
            )["p"] or 0
            if fee_pending > 0:
                risk_score += 10
                reasons.append(f"Fee pending: ₹{fee_pending}")

            if risk_score >= 30:
                at_risk.append({
                    "student_id": student.id,
                    "name": student.user.get_full_name(),
                    "class": str(student.current_class),
                    "risk_score": risk_score,
                    "risk_level": (
                        "HIGH" if risk_score >= 60 else
                        "MEDIUM" if risk_score >= 40 else "LOW"
                    ),
                    "reasons": reasons,
                    "attendance_pct": round(att_pct, 1),
                    "avg_marks": round(avg_marks, 1) if avg_marks else None,
                    "fee_pending": fee_pending,
                })

        at_risk.sort(key=lambda x: x["risk_score"], reverse=True)
        return Response({"at_risk_students": at_risk, "total": len(at_risk)})


class AIMarksPredictionView(APIView):
    def post(self, request):
        """Predict next exam marks based on trend."""
        student_id = request.data.get("student_id")
        subject_id = request.data.get("subject_id")

        if not (student_id and subject_id):
            return Response({"error": "student_id and subject_id required."}, status=400)

        marks = list(
            Mark.objects.filter(
                student_id=student_id,
                subject_id=subject_id,
            ).order_by("exam__date").values_list("percentage", flat=True)
        )

        if len(marks) < 2:
            return Response({"error": "Not enough data for prediction (need ≥ 2 exams)."}, status=400)

        # Simple linear regression
        n = len(marks)
        x_mean = (n - 1) / 2
        y_mean = sum(marks) / n
        numerator = sum((i - x_mean) * (marks[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator else 0
        intercept = y_mean - slope * x_mean
        predicted = round(intercept + slope * n, 1)
        predicted = max(0, min(100, predicted))  # Clamp 0-100

        trend = "improving" if slope > 2 else "declining" if slope < -2 else "stable"

        return Response({
            "marks_history": marks,
            "predicted_next": predicted,
            "trend": trend,
            "slope": round(slope, 2),
        })


# ══════════════════════════════════════════════════════════════════════════════
# PDF REPORT VIEWS
# ══════════════════════════════════════════════════════════════════════════════

def _build_pdf_doc(title, filename):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75*inch)
    return buffer, doc


def _pdf_header(elements, title, subtitle=""):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#1a237e"))
    elements.append(Paragraph("Durai Tuition Centre", title_style))
    if subtitle:
        elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Paragraph(title, styles["Heading2"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#f5a623")))
    elements.append(Spacer(1, 0.2*inch))


class AttendancePDFView(APIView):
    permission_classes = [IsAdminOrTeacher]

    def get(self, request):
        class_id = request.query_params.get("class_id")
        start = request.query_params.get("start", str(date.today() - timedelta(days=30)))
        end = request.query_params.get("end", str(date.today()))

        qs = Attendance.objects.filter(date__range=[start, end])
        if class_id:
            qs = qs.filter(class_ref_id=class_id)
            cls = Class.objects.get(pk=class_id)
            cls_name = str(cls)
        else:
            cls_name = "All Classes"

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        _pdf_header(elements, f"Attendance Report — {cls_name}", f"Period: {start} to {end}")

        # Aggregate
        summary = qs.values(
            "student__user__first_name", "student__user__last_name"
        ).annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status="P")),
            absent=Count("id", filter=Q(status="A")),
        ).order_by("student__user__last_name")

        data = [["Student Name", "Total Days", "Present", "Absent", "Attendance %"]]
        for row in summary:
            name = f"{row['student__user__first_name']} {row['student__user__last_name']}"
            total = row["total"]
            present = row["present"]
            pct = round(present / total * 100, 1) if total else 100.0
            data.append([name, total, present, row["absent"], f"{pct}%"])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="attendance_{start}_{end}.pdf"'
        return response


class ResultPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exam_id = request.query_params.get("exam_id")
        class_id = request.query_params.get("class_id")

        marks_qs = Mark.objects.select_related("student__user", "subject", "exam")
        if exam_id:
            marks_qs = marks_qs.filter(exam_id=exam_id)
        if class_id:
            marks_qs = marks_qs.filter(student__current_class_id=class_id)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        _pdf_header(elements, "Exam Results Report", f"Generated: {date.today()}")

        data = [["Student", "Exam", "Subject", "Marks", "Total", "%", "Grade"]]
        for m in marks_qs.order_by("student__user__last_name"):
            data.append([
                m.student.user.get_full_name(),
                m.exam.name,
                m.subject.name,
                m.marks_obtained,
                m.total_marks,
                f"{m.percentage}%",
                m.grade,
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="results.pdf"'
        return response


class FeePDFView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        academic_year = request.query_params.get("academic_year", "2024-25")
        fees = Fee.objects.filter(academic_year=academic_year).select_related("student__user")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        _pdf_header(elements, f"Fee Report — {academic_year}")

        total_due = fees.aggregate(Sum("amount"))["amount__sum"] or 0
        total_paid = fees.aggregate(Sum("amount_paid"))["amount_paid__sum"] or 0
        total_pending = total_due - total_paid

        styles = getSampleStyleSheet()
        elements.append(Paragraph(
            f"Total Due: ₹{total_due:,.2f} | Collected: ₹{total_paid:,.2f} | Pending: ₹{total_pending:,.2f}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 0.2*inch))

        data = [["Student", "Fee Type", "Amount", "Paid", "Balance", "Due Date", "Status"]]
        for fee in fees.order_by("student__user__last_name"):
            data.append([
                fee.student.user.get_full_name(),
                fee.get_fee_type_display(),
                f"₹{fee.amount:,.0f}",
                f"₹{fee.amount_paid:,.0f}",
                f"₹{fee.balance:,.0f}",
                str(fee.due_date),
                fee.status.upper(),
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="fees_{academic_year}.pdf"'
        return response


class StudentReportPDFView(APIView):
    def get(self, request, pk):
        student = Student.objects.select_related("user", "current_class", "parent__user").get(pk=pk)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        _pdf_header(elements, f"Student Progress Report — {student.user.get_full_name()}")

        # Personal details
        elements.append(Paragraph("Student Information", styles["Heading3"]))
        personal_data = [
            ["Name", student.user.get_full_name()],
            ["Admission No.", student.admission_number],
            ["Class", str(student.current_class)],
            ["Parent", student.parent.user.get_full_name() if student.parent else "—"],
            ["Contact", student.user.phone or "—"],
        ]
        personal_table = Table(personal_data, colWidths=[2*inch, 4*inch])
        personal_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eaf6")),
        ]))
        elements.append(personal_table)
        elements.append(Spacer(1, 0.2*inch))

        # Attendance
        att_total = Attendance.objects.filter(student=student).count()
        att_present = Attendance.objects.filter(student=student, status="P").count()
        att_pct = round(att_present / att_total * 100, 1) if att_total else 100.0

        elements.append(Paragraph("Attendance Summary", styles["Heading3"]))
        att_data = [
            ["Total Days", "Present", "Absent", "Attendance %"],
            [att_total, att_present, att_total - att_present, f"{att_pct}%"],
        ]
        att_table = Table(att_data)
        att_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(att_table)
        elements.append(Spacer(1, 0.2*inch))

        # Marks
        elements.append(Paragraph("Exam Results", styles["Heading3"]))
        marks = Mark.objects.filter(student=student).select_related("exam", "subject").order_by("exam__date")
        if marks:
            marks_data = [["Exam", "Subject", "Marks", "Total", "%", "Grade"]]
            for m in marks:
                marks_data.append([
                    m.exam.name, m.subject.name,
                    m.marks_obtained, m.total_marks,
                    f"{m.percentage}%", m.grade,
                ])
            marks_table = Table(marks_data, repeatRows=1)
            marks_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            elements.append(marks_table)

        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="report_{student.admission_number}.pdf"'
        return response


# ══════════════════════════════════════════════════════════════════════════════
# WHATSAPP WEBHOOK
# ══════════════════════════════════════════════════════════════════════════════

class WhatsAppWebhookView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """Webhook verification by Meta."""
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "durai_tuition_token")
        if mode == "subscribe" and token == verify_token:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse(status=403)

    def post(self, request):
        """Handle incoming WhatsApp messages."""
        data = request.data
        try:
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                from_number = msg.get("from")
                text = msg.get("text", {}).get("body", "")
                msg_type = msg.get("type")

                logger.info(f"WhatsApp message from {from_number}: {text}")

                # Log incoming message
                WhatsAppLog.objects.create(
                    phone_number=from_number,
                    message=text,
                    message_type="incoming",
                    status="received",
                )

                # Auto-reply with AI if it's a question
                if msg_type == "text" and "?" in text:
                    self._send_auto_reply(from_number, text)

        except Exception as e:
            logger.error(f"WhatsApp webhook error: {e}")

        return Response({"status": "ok"})

    def _send_auto_reply(self, phone, question):
        """Use AI to answer parent/student WhatsApp queries."""
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": (
                        f"You are the AI assistant for Durai Tuition Centre. "
                        f"Answer briefly (under 150 words): {question}"
                    )}],
                },
                timeout=15,
            )
            reply = resp.json()["content"][0]["text"]

            # Send reply via WhatsApp
            requests.post(
                f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": reply},
                },
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Auto-reply error: {e}")


# ── Custom error handlers ──────────────────────
def custom_404(request, exception):
    return JsonResponse({"error": "Not found."}, status=404)


def custom_500(request):
    return JsonResponse({"error": "Internal server error."}, status=500)
