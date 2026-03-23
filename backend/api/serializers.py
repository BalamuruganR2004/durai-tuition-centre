from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    User, Student, Parent, Teacher, Class, Subject, ClassSubject,
    Attendance, Exam, Mark, Note, Homework, HomeworkSubmission,
    Fee, Payment, Timetable, WhatsAppLog, SMSLog, AILog,
    Notification,
)


# ── Auth ──────────────────────────────────────
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        data["user"] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role",
                  "phone", "whatsapp_number", "profile_picture", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data


# ── Classes & Subjects ────────────────────────
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"


class ClassSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)
    student_count = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = ["id", "name", "grade", "section", "academic_year",
                  "class_teacher", "teacher_name", "subjects", "student_count",
                  "created_at"]

    def get_student_count(self, obj):
        return obj.students.count()

    def get_teacher_name(self, obj):
        if obj.class_teacher:
            return obj.class_teacher.user.get_full_name()
        return None


# ── Parent ────────────────────────────────────
class ParentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = ["id", "user", "occupation", "address", "alternate_phone",
                  "children_count", "created_at"]

    def get_children_count(self, obj):
        return obj.children.count()

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = User.objects.create_user(**user_data, role="parent")
        return Parent.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        return super().update(instance, validated_data)


# ── Teacher ───────────────────────────────────
class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    subjects = SubjectSerializer(many=True, read_only=True)
    classes_count = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ["id", "user", "employee_id", "qualification", "specialization",
                  "subjects", "classes_count", "joining_date", "is_active", "created_at"]

    def get_classes_count(self, obj):
        return obj.classes.count()

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = User.objects.create_user(**user_data, role="teacher")
        return Teacher.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        return super().update(instance, validated_data)


# ── Student ───────────────────────────────────
class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    parent_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    attendance_percentage = serializers.SerializerMethodField()
    average_marks = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "user", "admission_number", "roll_number",
                  "current_class", "class_name", "parent", "parent_name",
                  "date_of_birth", "gender", "blood_group", "address",
                  "photo", "is_active", "attendance_percentage",
                  "average_marks", "created_at"]

    def get_parent_name(self, obj):
        if obj.parent:
            return obj.parent.user.get_full_name()
        return None

    def get_class_name(self, obj):
        if obj.current_class:
            return str(obj.current_class)
        return None

    def get_attendance_percentage(self, obj):
        from django.db.models import Count, Q
        total = Attendance.objects.filter(student=obj).count()
        if total == 0:
            return 100.0
        present = Attendance.objects.filter(student=obj, status="P").count()
        return round((present / total) * 100, 1)

    def get_average_marks(self, obj):
        marks = Mark.objects.filter(student=obj)
        if not marks.exists():
            return None
        total = sum(m.percentage for m in marks)
        return round(total / marks.count(), 1)

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = User.objects.create_user(**user_data, role="student")
        return Student.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        return super().update(instance, validated_data)


# ── Attendance ────────────────────────────────
class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "student", "student_name", "class_ref", "subject",
                  "subject_name", "date", "status", "remarks",
                  "notification_sent", "created_at"]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name()

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject else None


class BulkAttendanceSerializer(serializers.Serializer):
    class_id = serializers.IntegerField()
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    date = serializers.DateField()
    records = serializers.ListField(
        child=serializers.DictField(),
        help_text="[{student_id: int, status: P|A|L|H, remarks: str}]"
    )


# ── Exams & Marks ─────────────────────────────
class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = "__all__"


class MarkSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()
    exam_name = serializers.SerializerMethodField()
    grade = serializers.ReadOnlyField()
    percentage = serializers.ReadOnlyField()

    class Meta:
        model = Mark
        fields = ["id", "student", "student_name", "exam", "exam_name",
                  "subject", "subject_name", "marks_obtained", "total_marks",
                  "grade", "percentage", "remarks", "created_at"]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name()

    def get_subject_name(self, obj):
        return obj.subject.name

    def get_exam_name(self, obj):
        return obj.exam.name


class StudentProgressSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    subject = serializers.CharField()
    exams = serializers.ListField(child=serializers.DictField())
    trend = serializers.CharField()  # improving / declining / stable


# ── Notes ─────────────────────────────────────
class NoteSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ["id", "title", "description", "file", "file_type",
                  "class_ref", "class_name", "subject", "subject_name",
                  "teacher", "teacher_name", "is_question_paper",
                  "is_active", "download_count", "created_at"]
        read_only_fields = ["download_count"]

    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name()

    def get_class_name(self, obj):
        return str(obj.class_ref)

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject else None


# ── Homework ──────────────────────────────────
class HomeworkSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = ["id", "title", "description", "file", "class_ref",
                  "class_name", "subject", "subject_name", "teacher",
                  "teacher_name", "assigned_date", "due_date",
                  "submission_count", "created_at"]

    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name()

    def get_subject_name(self, obj):
        return obj.subject.name

    def get_class_name(self, obj):
        return str(obj.class_ref)

    def get_submission_count(self, obj):
        return obj.submissions.count()


class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkSubmission
        fields = "__all__"


# ── Fees ──────────────────────────────────────
class FeeSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    balance = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = Fee
        fields = ["id", "student", "student_name", "fee_type", "amount",
                  "amount_paid", "balance", "status", "due_date",
                  "academic_year", "month", "remarks",
                  "receipt_number", "created_at", "updated_at"]

    def get_student_name(self, obj):
        return obj.student.user.get_full_name()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["payment_date"]


# ── Timetable ─────────────────────────────────
class TimetableSerializer(serializers.ModelSerializer):
    subject_name = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()

    class Meta:
        model = Timetable
        fields = ["id", "class_ref", "class_name", "subject", "subject_name",
                  "teacher", "teacher_name", "day_of_week", "start_time",
                  "end_time", "room_number"]

    def get_subject_name(self, obj):
        return obj.subject.name

    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name()

    def get_class_name(self, obj):
        return str(obj.class_ref)


# ── Notifications & Logs ──────────────────────
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "user", "title", "message", "notification_type",
                  "is_read", "created_at"]
        read_only_fields = ["created_at"]


class WhatsAppLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppLog
        fields = "__all__"
        read_only_fields = ["sent_at"]


class SMSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSLog
        fields = "__all__"
        read_only_fields = ["sent_at"]


class AILogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AILog
        fields = "__all__"
        read_only_fields = ["created_at"]