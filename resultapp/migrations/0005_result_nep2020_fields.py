from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resultapp', '0004_student_photo_alter_attendance_id_alter_class_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='theory_marks',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='result',
            name='internal_marks',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='result',
            name='practical_marks',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='result',
            name='oral_marks',
            field=models.IntegerField(null=True, blank=True),
        ),
        # Migrate existing marks: treat old `marks` as theory+internal combined (out of 50)
        # theory = int(marks * 30/50), internal = marks - theory
        migrations.RunSQL(
            sql="""
                UPDATE resultapp_result
                SET theory_marks   = CAST(ROUND(marks * 30.0 / 50) AS INTEGER),
                    internal_marks = marks - CAST(ROUND(marks * 30.0 / 50) AS INTEGER)
                WHERE marks <= 50;

                UPDATE resultapp_result
                SET theory_marks   = 30,
                    internal_marks = 20
                WHERE marks > 50;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
