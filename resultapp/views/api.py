from rest_framework import viewsets, serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from resultapp.models import Student, Result, Parent, Teacher, Class

class StudentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='student_class.class_name', read_only=True)
    section = serializers.CharField(source='student_class.section', read_only=True)
    branch_name = serializers.CharField(source='student_class.branch.branch_name', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'name', 'roll_id', 'email', 'gender', 'dob',
            'class_name', 'section', 'branch_name', 'status',
            'phone', 'address', 'emergency_contact_name', 'emergency_contact_phone',
            'blood_group'
        ]

class ResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    roll_id = serializers.CharField(source='student.roll_id', read_only=True)
    class_name = serializers.CharField(source='student_class.class_name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    total_obtained = serializers.IntegerField(read_only=True)
    total_max = serializers.IntegerField(read_only=True)
    subject_percentage = serializers.FloatField(read_only=True)
    nep_grade = serializers.CharField(read_only=True)
    nep_grade_point = serializers.IntegerField(read_only=True)
    is_subject_pass = serializers.BooleanField(read_only=True)

    class Meta:
        model = Result
        fields = [
            'id', 'student_name', 'roll_id', 'class_name', 'subject_name', 'subject_code',
            'semester', 'theory_marks', 'internal_marks', 'practical_marks', 'oral_marks',
            'total_obtained', 'total_max', 'subject_percentage', 'nep_grade', 'nep_grade_point',
            'is_subject_pass'
        ]

class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 1. Admin (superuser) sees all students
        if user.is_superuser:
            return Student.objects.all().select_related('student_class__branch')
        
        # 2. Teacher sees students in their assigned classes
        teacher = Teacher.objects.filter(user=user).first()
        if teacher:
            assigned_classes = teacher.assigned_classes.all()
            return Student.objects.filter(student_class__in=assigned_classes).select_related('student_class__branch')

        # 3. Parent sees their linked student
        parent = Parent.objects.filter(user=user).first()
        if parent:
            return Student.objects.filter(id=parent.student.id).select_related('student_class__branch')

        # 4. Student sees their own record
        student = Student.objects.filter(user=user).first()
        if student:
            return Student.objects.filter(id=student.id).select_related('student_class__branch')

        # Fallback empty list
        return Student.objects.none()

class ResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResultSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 1. Admin (superuser) sees all results
        if user.is_superuser:
            return Result.objects.all().select_related('student', 'student_class', 'subject')

        # 2. Teacher sees results in their assigned classes
        teacher = Teacher.objects.filter(user=user).first()
        if teacher:
            assigned_classes = teacher.assigned_classes.all()
            return Result.objects.filter(student_class__in=assigned_classes).select_related('student', 'student_class', 'subject')

        # 3. Parent sees results of their linked student
        parent = Parent.objects.filter(user=user).first()
        if parent:
            return Result.objects.filter(student=parent.student).select_related('student', 'student_class', 'subject')

        # 4. Student sees their own results
        student = Student.objects.filter(user=user).first()
        if student:
            return Result.objects.filter(student=student).select_related('student', 'student_class', 'subject')

        # Fallback empty list
        return Result.objects.none()
