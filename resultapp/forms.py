from django import forms
from .models import Class, Subject, Student, SubjectCombination, Result, Notice, Parent, Attendance, ProgressReport

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['class_name', 'class_numeric', 'section']
        widgets = {
            'class_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Class Name'}),
            'class_numeric': forms.NumberInput(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Section (e.g., A)'}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['subject_name', 'subject_code']
        widgets = {
            'subject_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Subject Name'}),
            'subject_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject Code'}),
        }

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'roll_id', 'email', 'gender', 'dob', 'student_class', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'roll_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Roll Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'student_class': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.NumberInput(attrs={'class': 'form-control'}), 
        }

class SubjectCombinationForm(forms.ModelForm):
    class Meta:
        model = SubjectCombination
        fields = ['student_class', 'subject']
        widgets = {
            'student_class': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
        }

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'student_class', 'subject', 'marks']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'student_class': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Marks Obtained'}),
        }

class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'detail']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notice Title'}),
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Notice Details'}),
        }

class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['phone', 'address', 'student', 'relationship']
        widgets = {
             'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
             'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
             'student': forms.Select(attrs={'class': 'form-select'}),
             'relationship': forms.Select(attrs={'class': 'form-select'}),
        }


class ProgressReportForm(forms.ModelForm):
    class Meta:
        model = ProgressReport
        fields = ['student', 'term', 'overall_percentage', 'grade', 'teacher_remarks', 'strengths', 'areas_of_improvement']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
             'term': forms.TextInput(attrs={'class': 'form-control'}),
             'overall_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
             'grade': forms.TextInput(attrs={'class': 'form-control'}),
             'teacher_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
             'strengths': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
             'areas_of_improvement': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
