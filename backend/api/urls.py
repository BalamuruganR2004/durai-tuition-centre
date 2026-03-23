from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"students",      views.StudentViewSet,      basename="student")
router.register(r"parents",       views.ParentViewSet,       basename="parent")
router.register(r"teachers",      views.TeacherViewSet,      basename="teacher")
router.register(r"classes",       views.ClassViewSet,        basename="class")
router.register(r"subjects",      views.SubjectViewSet,      basename="subject")
router.register(r"attendance",    views.AttendanceViewSet,   basename="attendance")
router.register(r"exams",         views.ExamViewSet,         basename="exam")
router.register(r"marks",         views.MarkViewSet,         basename="mark")
router.register(r"notes",         views.NoteViewSet,         basename="note")
router.register(r"homework",      views.HomeworkViewSet,     basename="homework")
router.register(r"fees",          views.FeeViewSet,          basename="fee")
router.register(r"payments",      views.PaymentViewSet,      basename="payment")
router.register(r"timetable",     views.TimetableViewSet,    basename="timetable")
router.register(r"whatsapp-logs", views.WhatsAppLogViewSet,  basename="whatsapp-log")
router.register(r"notifications", views.NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),

    # Auth
    path("auth/login/",    views.LoginView.as_view(),    name="login"),
    path("auth/logout/",   views.LogoutView.as_view(),   name="logout"),
    path("auth/profile/",  views.ProfileView.as_view(),  name="profile"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="change-password"),

    # AI
    path("ai/chat/",            views.AIChatView.as_view(),           name="ai-chat"),
    path("ai/study-plan/",      views.AIStudyPlanView.as_view(),       name="ai-study-plan"),
    path("ai/analytics/",       views.AIAnalyticsView.as_view(),       name="ai-analytics"),
    path("ai/predict-marks/",   views.AIMarksPredictionView.as_view(), name="ai-predict-marks"),

    # Reports (PDF)
    path("reports/attendance/", views.AttendancePDFView.as_view(), name="report-attendance"),
    path("reports/results/",    views.ResultPDFView.as_view(),     name="report-results"),
    path("reports/fees/",       views.FeePDFView.as_view(),        name="report-fees"),
    path("reports/student/<int:pk>/", views.StudentReportPDFView.as_view(), name="report-student"),

    # Dashboard stats
    path("dashboard/admin/",   views.AdminDashboardView.as_view(),   name="dashboard-admin"),
    path("dashboard/teacher/", views.TeacherDashboardView.as_view(), name="dashboard-teacher"),
    path("dashboard/student/", views.StudentDashboardView.as_view(), name="dashboard-student"),
    path("dashboard/parent/",  views.ParentDashboardView.as_view(),  name="dashboard-parent"),

    # WhatsApp webhook
    path("webhooks/whatsapp/", views.WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]