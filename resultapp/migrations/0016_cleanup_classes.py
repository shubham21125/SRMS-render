from django.db import migrations

def cleanup_classes(apps, schema_editor):
    Class = apps.get_model('resultapp', 'Class')
    Student = apps.get_model('resultapp', 'Student')
    Result = apps.get_model('resultapp', 'Result')
    Exam = apps.get_model('resultapp', 'Exam')
    SubjectCombination = apps.get_model('resultapp', 'SubjectCombination')
    Parent = apps.get_model('resultapp', 'Parent')
    User = apps.get_model('auth', 'User')

    # 1. Merge Class 1 ("First Year CS") into Class 13 ("First Year B.Sc. Computer Science")
    class1 = Class.objects.filter(id=1).first()
    class13 = Class.objects.filter(id=13).first()

    if class1 and class13:
        # Reassign Student 1 ("Shubham") to Class 13
        Student.objects.filter(student_class_id=1).update(student_class_id=13)
        # Reassign Student 1's results to Class 13
        Result.objects.filter(student_class_id=1).update(student_class_id=13)
        # Reassign Exams to Class 13
        Exam.objects.filter(student_class_id=1).update(student_class_id=13)

        # Reassign Teacher assigned classes from 1 to 13
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("UPDATE resultapp_teacher_assigned_classes SET class_id = 13 WHERE class_id = 1")

        # Delete stale duplicate Class 1
        class1.delete()

    # 2. Purge Student 2 ("Rahul Sharma") and legacy Classes 9, 10, 11, 12
    # Delete Parent and linked User for Student 2
    for parent in Parent.objects.filter(student_id=2):
        if parent.user_id:
            User.objects.filter(id=parent.user_id).delete()
        parent.delete()

    # Delete Student 2's results
    Result.objects.filter(student_id=2).delete()

    # Delete Student 2
    Student.objects.filter(id=2).delete()

    # Delete SubjectCombinations for legacy classes
    SubjectCombination.objects.filter(student_class_id__in=[9, 10, 11, 12]).delete()

    # Delete Classes 9, 10, 11, 12
    Class.objects.filter(id__in=[9, 10, 11, 12]).delete()

def reverse_cleanup(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('resultapp', '0015_alter_attendance_date_alter_auditlog_target_model_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_classes, reverse_cleanup),
    ]
