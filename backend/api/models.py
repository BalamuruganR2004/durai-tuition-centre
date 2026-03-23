"""
================================================================
DURAI TUITION CENTRE — DJANGO BACKEND
================================================================
Tech Stack: Django 4.2 + DRF + PostgreSQL
Auth: JWT (djangorestframework-simplejwt)
WhatsApp: Meta Business API / Twilio
AI: Anthropic Claude API
Cloud: Railway / Render / AWS EC2 ready
================================================================

INSTALLATION:
pip install django djangorestframework djangorestframework-simplejwt
         django-cors-headers psycopg2-binary anthropic twilio
         reportlab celery redis django-filter pillow boto3

SETUP:
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
================================================================
"""

# ============================================================
# PROJECT STRUCTURE
# ============================================================
"""
durai_tuition_backend/
├── manage.py
├── requirements.txt
├── .env
├── durai_backend/
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
└── apps/
    ├── accounts/        (User auth, roles)
    ├── students/        (Student management)
    ├── teachers/        (Teacher portal)
    ├── classes/         (Class & subject mgmt)
    ├── attendance/      (Attendance + alerts)
    ├── exams/           (Exams & marks)
    ├── notes/           (Study materials)
    ├── homework/        (Homework)
    ├── fees/            (Fee management)
    ├── notifications/   (WhatsApp + SMS)
    ├── ai_engine/       (AI features)
    └── reports/         (PDF reports)
"""

# ============================================================
# settings.py
# ============================================================
SETTINGS_PY = """
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    # Local apps
    'apps.accounts',
    'apps.students',
    'apps.teachers',
    'apps.classes',
    'apps.attendance',
    'apps.exams',
    'apps.notes',
    'apps.homework',
    'apps.fees',
    'apps.notifications',
    'apps.ai_engine',
    'apps.reports',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'durai_tuition'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://duraitc.com",
]
CORS_ALLOW_CREDENTIALS = True

AUTH_USER_MODEL = 'accounts.User'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Celery (background tasks)
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# WhatsApp API
WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', '')

# SMS (MSG91)
MSG91_API_KEY = os.getenv('MSG91_API_KEY', '')
MSG91_SENDER_ID = 'DURAITC'

# AI
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# AWS S3 (for file storage in production)
USE_S3 = os.getenv('USE_S3', 'False') == 'True'
if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = 'ap-south-1'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
"""

# ============================================================
# MODELS
# ============================================================

MODELS_PY = """
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]
    role = models.CharField(max_length=20, choices=ROLES, default='student')
    phone = models.CharField(max_length=15, blank=True)
    whatsapp_number = models.CharField(max_length=15, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'


# apps/classes/models.py
class Class(models.Model):
    name = models.CharField(max_length=20)  # e.g. '10A'
    grade = models.IntegerField()           # 6-12
    section = models.CharField(max_length=5)
    academic_year = models.CharField(max_length=10, default='2024-25')
    class_teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'classes'
        unique_together = ['name', 'academic_year']

    def __str__(self): return f"Class {self.name}"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    grade = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'subjects'


class ClassSubject(models.Model):
    \"\"\"Assign a subject + teacher to a class\"\"\"
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'class_subjects'
        unique_together = ['class_instance', 'subject']


# apps/students/models.py
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    class_assigned = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('M','Male'),('F','Female'),('O','Other')])
    address = models.TextField(blank=True)
    monthly_fee = models.DecimalField(max_digits=8, decimal_places=2, default=3500.00)
    admission_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'students'

    def __str__(self): return self.user.get_full_name()


class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    students = models.ManyToManyField(Student, related_name='parents')
    relation = models.CharField(max_length=20, default='Parent')
    occupation = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'parents'


# apps/teachers/models.py
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    teacher_id = models.CharField(max_length=20, unique=True)
    subjects = models.ManyToManyField(Subject)
    qualification = models.CharField(max_length=200, blank=True)
    experience_years = models.IntegerField(default=0)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    joining_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'teachers'


# apps/attendance/models.py
class AttendanceRecord(models.Model):
    STATUS_CHOICES = [('P','Present'),('A','Absent'),('L','Late'),('H','Holiday')]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True)
    notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attendance'
        unique_together = ['student', 'date', 'subject']


# apps/exams/models.py
class Exam(models.Model):
    TYPES = [
        ('unit_test','Unit Test'),
        ('quarterly','Quarterly'),
        ('half_yearly','Half Yearly'),
        ('model','Model Exam'),
        ('final','Final Exam'),
    ]
    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=TYPES)
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    max_marks = models.IntegerField(default=100)
    pass_marks = models.IntegerField(default=35)
    duration_minutes = models.IntegerField(default=180)
    status = models.CharField(max_length=20, default='upcoming',
                               choices=[('upcoming','Upcoming'),('ongoing','Ongoing'),('completed','Completed')])
    created_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exams'


class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    is_absent = models.BooleanField(default=False)
    entered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marks'
        unique_together = ['student', 'exam', 'subject']

    @property
    def percentage(self):
        return (self.marks_obtained / self.exam.max_marks) * 100

    @property
    def grade(self):
        p = self.percentage
        if p >= 90: return 'A+'
        elif p >= 80: return 'A'
        elif p >= 70: return 'B+'
        elif p >= 60: return 'B'
        elif p >= 50: return 'C'
        elif p >= 35: return 'D'
        return 'F'


# apps/notes/models.py
class Note(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    file = models.FileField(upload_to='notes/%Y/%m/')
    file_type = models.CharField(max_length=20, default='PDF')
    description = models.TextField(blank=True)
    is_question_paper = models.BooleanField(default=False)
    download_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notes'


# apps/homework/models.py
class Homework(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    due_date = models.DateField()
    max_marks = models.IntegerField(null=True, blank=True)
    attachment = models.FileField(upload_to='homework/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'homework'


class HomeworkSubmission(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    submission_file = models.FileField(upload_to='submissions/', null=True, blank=True)
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    marks_given = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        db_table = 'homework_submissions'


# apps/fees/models.py
class FeeStructure(models.Model):
    grade = models.IntegerField()
    monthly_fee = models.DecimalField(max_digits=8, decimal_places=2)
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    material_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    academic_year = models.CharField(max_length=10)

    class Meta:
        db_table = 'fee_structure'


class FeeRecord(models.Model):
    STATUS = [('pending','Pending'),('paid','Paid'),('partial','Partial'),('overdue','Overdue'),('waived','Waived')]
    PAYMENT_MODES = [('cash','Cash'),('upi','UPI'),('bank','Bank Transfer'),('cheque','Cheque')]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    month = models.DateField()  # 1st of the fee month
    amount_due = models.DecimalField(max_digits=8, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    due_date = models.DateField()
    late_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    receipt_number = models.CharField(max_length=50, blank=True)
    collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reminder_count = models.IntegerField(default=0)
    last_reminder_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fees'
        unique_together = ['student', 'month']

    @property
    def balance(self):
        return self.amount_due - self.amount_paid + self.late_fee


# apps/notifications/models.py
class WhatsAppLog(models.Model):
    recipient_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    message_type = models.CharField(max_length=50, default='custom')
    status = models.CharField(max_length=20, default='pending')
    whatsapp_message_id = models.CharField(max_length=100, blank=True)
    related_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'whatsapp_logs'


class SMSLog(models.Model):
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20)
    provider_id = models.CharField(max_length=100, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sms_logs'


# apps/ai_engine/models.py
class AILog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField()
    response = models.TextField()
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_logs'


class TimetableEntry(models.Model):
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()  # 0=Mon ... 5=Sat
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'timetable'
"""

# ============================================================
# API VIEWS
# ============================================================

VIEWS_PY = """
# apps/accounts/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .serializers import UserSerializer


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'name': user.get_full_name(),
                    'email': user.email,
                    'role': user.role,
                }
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def refresh_token(self, request):
        try:
            refresh = RefreshToken(request.data.get('refresh'))
            return Response({'access': str(refresh.access_token)})
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


# apps/attendance/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AttendanceRecord
from .serializers import AttendanceSerializer
from apps.notifications.tasks import send_absence_notification


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    filterset_fields = ['student', 'date', 'status', 'class_instance']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return AttendanceRecord.objects.filter(marked_by=user.teacher)
        elif user.role == 'student':
            return AttendanceRecord.objects.filter(student=user.student)
        elif user.role == 'parent':
            students = user.parent.students.all()
            return AttendanceRecord.objects.filter(student__in=students)
        return AttendanceRecord.objects.all()

    @action(detail=False, methods=['post'])
    def bulk_mark(self, request):
        \"\"\"Mark attendance for entire class at once\"\"\"
        records = request.data.get('records', [])
        class_id = request.data.get('class_id')
        date = request.data.get('date')
        subject_id = request.data.get('subject_id')
        absent_students = []

        for record in records:
            obj, created = AttendanceRecord.objects.update_or_create(
                student_id=record['student_id'],
                date=date,
                subject_id=subject_id,
                defaults={
                    'status': record['status'],
                    'class_instance_id': class_id,
                    'marked_by': request.user.teacher,
                }
            )
            if record['status'] == 'A' and not obj.notification_sent:
                absent_students.append(record['student_id'])

        # Send WhatsApp to absent students' parents
        for student_id in absent_students:
            send_absence_notification.delay(student_id, date)

        return Response({'message': f'Attendance marked. Alerts sent for {len(absent_students)} absent students.'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        \"\"\"Get attendance summary for a student or class\"\"\"
        student_id = request.query_params.get('student_id')
        if student_id:
            records = AttendanceRecord.objects.filter(student_id=student_id)
            total = records.count()
            present = records.filter(status='P').count()
            percentage = (present / total * 100) if total > 0 else 0
            return Response({
                'total': total, 'present': present,
                'absent': total - present,
                'percentage': round(percentage, 2)
            })
        return Response({'error': 'student_id required'}, status=400)


# apps/exams/views.py
class ExamViewSet(viewsets.ModelViewSet):
    filterset_fields = ['class_instance', 'subject', 'status', 'exam_type']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return Exam.objects.filter(class_instance=user.student.class_assigned)
        if user.role == 'teacher':
            return Exam.objects.filter(created_by=user.teacher)
        if user.role == 'parent':
            classes = {s.class_assigned for s in user.parent.students.all()}
            return Exam.objects.filter(class_instance__in=classes)
        return Exam.objects.all()


class MarkViewSet(viewsets.ModelViewSet):
    filterset_fields = ['student', 'exam', 'subject']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return Mark.objects.filter(student=user.student)
        if user.role == 'parent':
            return Mark.objects.filter(student__in=user.parent.students.all())
        return Mark.objects.all()

    @action(detail=False, methods=['get'])
    def progress(self, request):
        \"\"\"Get mark progression for a student across exams\"\"\"
        student_id = request.query_params.get('student_id')
        subject_id = request.query_params.get('subject_id')
        marks = Mark.objects.filter(student_id=student_id)
        if subject_id:
            marks = marks.filter(subject_id=subject_id)
        data = [{
            'exam': m.exam.name,
            'date': m.exam.date,
            'marks': float(m.marks_obtained),
            'percentage': m.percentage,
            'grade': m.grade
        } for m in marks.order_by('exam__date')]
        return Response(data)


# apps/fees/views.py
class FeeViewSet(viewsets.ModelViewSet):
    filterset_fields = ['student', 'status', 'month']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return FeeRecord.objects.filter(student=user.student)
        if user.role == 'parent':
            return FeeRecord.objects.filter(student__in=user.parent.students.all())
        return FeeRecord.objects.all()

    @action(detail=False, methods=['post'])
    def record_payment(self, request):
        fee_id = request.data.get('fee_id')
        amount = request.data.get('amount')
        payment_mode = request.data.get('payment_mode', 'cash')
        ref = request.data.get('transaction_ref', '')

        fee = FeeRecord.objects.get(id=fee_id)
        fee.amount_paid += Decimal(amount)
        fee.payment_mode = payment_mode
        fee.transaction_ref = ref
        fee.payment_date = date.today()
        fee.status = 'paid' if fee.amount_paid >= fee.amount_due else 'partial'
        fee.receipt_number = f'FC-{date.today().year}-{fee.id:04d}'
        fee.save()

        # Send receipt via WhatsApp
        send_fee_receipt.delay(fee.id)
        return Response({'message': 'Payment recorded', 'receipt': fee.receipt_number})

    @action(detail=False, methods=['post'])
    def send_reminders(self, request):
        \"\"\"Send fee reminders to all pending/overdue students\"\"\"
        pending = FeeRecord.objects.filter(status__in=['pending', 'overdue', 'partial'])
        count = 0
        for fee in pending:
            send_fee_reminder.delay(fee.id)
            count += 1
        return Response({'message': f'Reminders sent to {count} students'})


# apps/ai_engine/views.py
import anthropic
from rest_framework.views import APIView


class AIChatView(APIView):
    def post(self, request):
        query = request.data.get('message', '')
        user = request.user

        # Build context based on role
        context = self.build_context(user, query)
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            system=context['system'],
            messages=[{'role': 'user', 'content': query}]
        )

        ai_reply = response.content[0].text

        # Log
        AILog.objects.create(
            user=user, query=query, response=ai_reply,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens
        )
        return Response({'reply': ai_reply})

    def build_context(self, user, query):
        if user.role == 'student':
            student = user.student
            attendance = AttendanceRecord.objects.filter(student=student)
            marks = Mark.objects.filter(student=student)
            system = f\"\"\"You are an AI study assistant for {student.user.get_full_name()}, 
            a student at Durai Tuition Centre in Class {student.class_assigned}.
            Attendance: {attendance.filter(status='P').count()}/{attendance.count()} days present.
            Help with: study plans, doubt clearing, exam tips, motivation.\"\"\"
        elif user.role == 'admin':
            system = \"\"\"You are the AI analytics assistant for Durai Tuition Centre admin.
            Help with: student performance analysis, fee collection insights, attendance trends,
            generating reports, identifying at-risk students, and management decisions.\"\"\"
        elif user.role == 'teacher':
            system = \"\"\"You are the AI teaching assistant for a teacher at Durai Tuition Centre.
            Help with: lesson planning, question generation, performance analysis, 
            student doubt resolution, and teaching strategies.\"\"\"
        else:
            system = \"\"\"You are the parent liaison AI for Durai Tuition Centre.
            Help parents understand their child's performance, attendance, and upcoming events.\"\"\"
        return {'system': system}


class AIAnalyticsView(APIView):
    def get(self, request):
        action = request.query_params.get('action', 'at_risk')

        if action == 'at_risk':
            return self.get_at_risk_students()
        elif action == 'predict_marks':
            student_id = request.query_params.get('student_id')
            return self.predict_marks(student_id)
        elif action == 'study_plan':
            student_id = request.query_params.get('student_id')
            return self.generate_study_plan(student_id)

    def get_at_risk_students(self):
        \"\"\"Identify students at risk based on attendance + marks\"\"\"
        from apps.students.models import Student
        from django.db.models import Avg

        at_risk = []
        students = Student.objects.filter(is_active=True)

        for student in students:
            att_records = AttendanceRecord.objects.filter(student=student)
            total = att_records.count()
            if total == 0: continue
            present = att_records.filter(status='P').count()
            att_pct = (present / total) * 100

            marks = Mark.objects.filter(student=student)
            avg_pct = marks.aggregate(avg=Avg('marks_obtained'))['avg'] or 0

            risk_score = 0
            reasons = []

            if att_pct < 75:
                risk_score += 40
                reasons.append(f'Attendance {att_pct:.0f}% (below 75%)')
            elif att_pct < 85:
                risk_score += 20

            if avg_pct < 35:
                risk_score += 50
                reasons.append(f'Average marks {avg_pct:.0f}% (below pass mark)')
            elif avg_pct < 50:
                risk_score += 30
                reasons.append(f'Average marks {avg_pct:.0f}% (needs improvement)')

            if risk_score > 30:
                at_risk.append({
                    'student_id': student.id,
                    'name': student.user.get_full_name(),
                    'class': str(student.class_assigned),
                    'attendance': round(att_pct, 1),
                    'avg_marks': round(float(avg_pct), 1),
                    'risk_score': risk_score,
                    'risk_level': 'High' if risk_score >= 60 else 'Medium' if risk_score >= 40 else 'Low',
                    'reasons': reasons,
                })

        at_risk.sort(key=lambda x: x['risk_score'], reverse=True)
        return Response({'at_risk_students': at_risk, 'count': len(at_risk)})
"""

# ============================================================
# CELERY TASKS (Background Jobs)
# ============================================================

TASKS_PY = """
# apps/notifications/tasks.py
from celery import shared_task
import requests
from django.conf import settings


@shared_task
def send_absence_notification(student_id, date_str):
    \"\"\"Send WhatsApp to parent when student is absent\"\"\"
    from apps.students.models import Student
    student = Student.objects.get(id=student_id)
    parents = student.parents.all()

    for parent in parents:
        if parent.user.whatsapp_number:
            message = (
                f"Dear {parent.user.get_full_name()},\\n\\n"
                f"This is to inform you that *{student.user.get_full_name()}* "
                f"was *absent* from Durai Tuition Centre today ({date_str}).\\n\\n"
                f"Please ensure regular attendance for better academic performance.\\n\\n"
                f"— Durai Tuition Centre"
            )
            send_whatsapp_message(parent.user.whatsapp_number, message, student_id)
            # Also update DB
            from apps.attendance.models import AttendanceRecord
            AttendanceRecord.objects.filter(
                student_id=student_id, date=date_str, status='A'
            ).update(notification_sent=True)


@shared_task
def send_fee_reminder(fee_id):
    \"\"\"Send WhatsApp fee reminder to parent\"\"\"
    from apps.fees.models import FeeRecord
    fee = FeeRecord.objects.get(id=fee_id)
    parents = fee.student.parents.all()

    for parent in parents:
        if parent.user.whatsapp_number:
            balance = fee.balance
            message = (
                f"Dear {parent.user.get_full_name()},\\n\\n"
                f"🔔 *Fee Reminder — Durai Tuition Centre*\\n\\n"
                f"Student: {fee.student.user.get_full_name()}\\n"
                f"Month: {fee.month.strftime('%B %Y')}\\n"
                f"Amount Due: ₹{balance:,.0f}\\n"
                f"Due Date: {fee.due_date.strftime('%d %B %Y')}\\n\\n"
                f"Please pay at your earliest convenience.\\n"
                f"For queries: {settings.CENTRE_PHONE}\\n\\n"
                f"— Durai Tuition Centre"
            )
            send_whatsapp_message(parent.user.whatsapp_number, message, fee.student.id)
            fee.reminder_count += 1
            from django.utils import timezone
            fee.last_reminder_at = timezone.now()
            fee.save()


@shared_task
def send_result_notification(mark_id):
    \"\"\"Send result to parent after marks entry\"\"\"
    from apps.exams.models import Mark
    mark = Mark.objects.get(id=mark_id)
    parents = mark.student.parents.all()

    for parent in parents:
        if parent.user.whatsapp_number:
            message = (
                f"📊 *Exam Result — Durai Tuition Centre*\\n\\n"
                f"Student: {mark.student.user.get_full_name()}\\n"
                f"Exam: {mark.exam.name}\\n"
                f"Subject: {mark.subject.name if mark.subject else 'All Subjects'}\\n"
                f"Marks: {mark.marks_obtained}/{mark.exam.max_marks}\\n"
                f"Grade: {mark.grade} ({mark.percentage:.0f}%)\\n\\n"
                f"{'🎉 Excellent work!' if mark.percentage >= 80 else '📚 Keep working hard!'}\\n\\n"
                f"— Durai Tuition Centre"
            )
            send_whatsapp_message(parent.user.whatsapp_number, message, mark.student.id)


def send_whatsapp_message(phone_number, message, student_id=None):
    \"\"\"Send WhatsApp via Meta Business API\"\"\"
    from apps.notifications.models import WhatsAppLog

    # Format phone number
    phone = phone_number.replace(' ', '').replace('+', '').replace('-', '')
    if not phone.startswith('91') and len(phone) == 10:
        phone = '91' + phone

    url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'text',
        'text': {'body': message}
    }

    log = WhatsAppLog.objects.create(
        phone_number=phone,
        message=message,
        status='sending',
        related_student_id=student_id
    )

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if response.status_code == 200:
            log.status = 'sent'
            log.whatsapp_message_id = data.get('messages', [{}])[0].get('id', '')
        else:
            log.status = 'failed'
    except Exception as e:
        log.status = 'error'
    finally:
        log.save()


@shared_task
def daily_attendance_alert():
    \"\"\"Run daily: check attendance < 75% and send alerts\"\"\"
    from apps.students.models import Student
    from apps.attendance.models import AttendanceRecord

    students = Student.objects.filter(is_active=True)
    for student in students:
        records = AttendanceRecord.objects.filter(student=student)
        total = records.count()
        if total < 10: continue
        present = records.filter(status='P').count()
        pct = (present / total) * 100
        if pct < 75:
            parents = student.parents.all()
            for parent in parents:
                message = (
                    f"⚠️ *Attendance Warning — Durai Tuition Centre*\\n\\n"
                    f"Dear {parent.user.get_full_name()},\\n"
                    f"{student.user.get_full_name()}'s attendance has dropped to "
                    f"*{pct:.0f}%* which is below the required 75%.\\n\\n"
                    f"Students with less than 75% attendance may not be eligible for exams.\\n"
                    f"Please contact us immediately.\\n\\n"
                    f"— Durai Tuition Centre"
                )
                send_whatsapp_message(parent.user.whatsapp_number, message, student.id)


@shared_task
def generate_monthly_fee_records():
    \"\"\"Create fee records for the new month (run on 1st of each month)\"\"\"
    from apps.students.models import Student
    from apps.fees.models import FeeRecord
    from datetime import date
    from dateutil.relativedelta import relativedelta

    today = date.today()
    month_start = today.replace(day=1)
    due_date = month_start.replace(day=10)

    students = Student.objects.filter(is_active=True)
    created = 0
    for student in students:
        _, was_created = FeeRecord.objects.get_or_create(
            student=student, month=month_start,
            defaults={
                'amount_due': student.monthly_fee,
                'due_date': due_date,
                'status': 'pending'
            }
        )
        if was_created: created += 1

    return f'Created {created} fee records for {month_start.strftime(\"%B %Y\")}'
"""

# ============================================================
# URLS
# ============================================================

URLS_PY = """
# durai_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from apps.accounts.views import AuthViewSet
from apps.students.views import StudentViewSet, ParentViewSet
from apps.teachers.views import TeacherViewSet
from apps.classes.views import ClassViewSet, SubjectViewSet
from apps.attendance.views import AttendanceViewSet
from apps.exams.views import ExamViewSet, MarkViewSet
from apps.notes.views import NoteViewSet
from apps.homework.views import HomeworkViewSet
from apps.fees.views import FeeViewSet
from apps.notifications.views import WhatsAppLogViewSet
from apps.ai_engine.views import AIChatView, AIAnalyticsView
from apps.reports.views import ReportView

router = DefaultRouter()
router.register('auth', AuthViewSet, basename='auth')
router.register('students', StudentViewSet)
router.register('parents', ParentViewSet)
router.register('teachers', TeacherViewSet)
router.register('classes', ClassViewSet)
router.register('subjects', SubjectViewSet)
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('exams', ExamViewSet, basename='exams')
router.register('marks', MarkViewSet, basename='marks')
router.register('notes', NoteViewSet)
router.register('homework', HomeworkViewSet)
router.register('fees', FeeViewSet, basename='fees')
router.register('whatsapp-logs', WhatsAppLogViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/ai/chat/', AIChatView.as_view()),
    path('api/v1/ai/analytics/', AIAnalyticsView.as_view()),
    path('api/v1/reports/', ReportView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""

print("Backend code structure created successfully.")
print("""
==================================================
API ENDPOINTS SUMMARY
==================================================
POST   /api/v1/auth/login/             — Login
POST   /api/v1/auth/refresh_token/     — Refresh JWT

GET    /api/v1/students/               — List students
POST   /api/v1/students/               — Create student
GET    /api/v1/students/{id}/          — Student detail
PUT    /api/v1/students/{id}/          — Update
DELETE /api/v1/students/{id}/          — Delete

GET    /api/v1/attendance/             — List records
POST   /api/v1/attendance/bulk_mark/   — Bulk attendance
GET    /api/v1/attendance/summary/     — Attendance %

GET    /api/v1/exams/                  — List exams
POST   /api/v1/marks/                  — Enter marks
GET    /api/v1/marks/progress/         — Mark history

GET    /api/v1/fees/                   — Fee records
POST   /api/v1/fees/record_payment/    — Record payment
POST   /api/v1/fees/send_reminders/    — Bulk reminders

GET    /api/v1/notes/                  — Study materials
POST   /api/v1/notes/                  — Upload material

GET    /api/v1/homework/               — List homework
POST   /api/v1/homework/               — Assign homework

GET    /api/v1/whatsapp-logs/          — WA message log

POST   /api/v1/ai/chat/               — AI chatbot
GET    /api/v1/ai/analytics/          — AI insights

GET    /api/v1/reports/               — Generate PDF reports
==================================================
""")
