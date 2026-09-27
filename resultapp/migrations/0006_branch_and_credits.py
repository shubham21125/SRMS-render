from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('resultapp', '0005_result_nep2020_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('branch_name', models.CharField(max_length=150)),
                ('branch_code', models.CharField(max_length=20, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('status', models.IntegerField(default=1)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('updation_date', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Branches',
                'ordering': ['branch_name'],
            },
        ),
        migrations.AddField(
            model_name='subject',
            name='credits',
            field=models.PositiveIntegerField(default=4, help_text='NEP 2020 credit value for this subject (e.g. 2, 3, 4)'),
        ),
        migrations.AddField(
            model_name='class',
            name='branch',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Programme / branch this class belongs to, e.g. BSc Computer Science',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='classes', to='resultapp.branch',
            ),
        ),
        migrations.CreateModel(
            name='BranchSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('semester', models.IntegerField(choices=[(1, 'Semester 1'), (2, 'Semester 2'), (3, 'Semester 3'), (4, 'Semester 4'), (5, 'Semester 5'), (6, 'Semester 6')], default=1)),
                ('status', models.IntegerField(default=1)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('updation_date', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branch_subjects', to='resultapp.branch')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resultapp.subject')),
            ],
            options={
                'verbose_name_plural': 'Branch Subjects',
                'ordering': ['branch', 'semester', 'subject'],
                'unique_together': {('branch', 'subject', 'semester')},
            },
        ),
    ]
