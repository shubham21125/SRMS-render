"""
Bulk seed script — BSc Computer Science (NEP 2020, University of Mumbai)
Creates: 1 Branch, 3 Classes (FYCS/SYCS/TYCS), 24 subjects across
6 semesters matching University of Mumbai's B.Sc. CS syllabus, 50
pan-India-named students per class (150 total), and results for every
student across all subjects of their applicable semesters.

Run with:
    python manage.py shell < scripts/seed_bulk_cs_students.py
"""
import random
from resultapp.models import Branch, Class, Subject, BranchSubject, SubjectCombination, Student, Result

random.seed(42)
print("=== Seeding BSc CS bulk demo data (FYCS / SYCS / TYCS) ===")

# ── Branch ─────────────────────────────────────────────────────────
branch, _ = Branch.objects.get_or_create(
    branch_code="BSCCS",
    defaults=dict(branch_name="BSc Computer Science", description="NEP 2020 Programme", status=1),
)

# ── Classes ────────────────────────────────────────────────────────
class_defs = [
    ("FYCS", "First Year B.Sc. Computer Science", 1, "A", [1, 2]),
    ("SYCS", "Second Year B.Sc. Computer Science", 2, "A", [3, 4]),
    ("TYCS", "Third Year B.Sc. Computer Science", 3, "A", [5, 6]),
]
classes = {}
for short, full_name, numeric, section, sems in class_defs:
    cls, _ = Class.objects.get_or_create(
        branch=branch, class_name=full_name, class_numeric=numeric, section=section,
    )
    classes[short] = {"obj": cls, "semesters": sems}

# ── University of Mumbai NEP 2020 subjects per semester (BSc Computer
#    Science — Major/core papers, drawn from University of Mumbai's
#    published NEP 2020 syllabus and B.Sc.CS study-material listings;
#    verify exact paper codes/credits against your college's affiliation
#    circular before using for an official transcript) ────────────────
subjects_by_sem = {
    1: [("Digital Systems & Architecture", "CS101", 2), ("Fundamentals of Database Systems", "CS102", 2),
        ("Introduction to Programming with Python", "CS103", 2), ("Communication Skills in English I", "CS104", 2)],
    2: [("Design and Analysis of Algorithms", "CS201", 2), ("Object Oriented Programming using C++", "CS202", 2),
        ("Web Designing", "CS203", 2), ("Database Management Systems using PL/SQL", "CS204", 2)],
    3: [("Operating System", "CS301", 3), ("Combinatorics and Graph Theory", "CS302", 3),
        ("Database Management Systems", "CS303", 3), ("Core Java", "CS304", 3)],
    4: [("Computer Networks", "CS401", 3), ("Advanced Java", "CS402", 3),
        ("Software Engineering", "CS403", 3), ("Fundamentals of Algorithms", "CS404", 3)],
    5: [("Artificial Intelligence", "CS501", 4), ("Information and Network Security", "CS502", 4),
        ("Linux Server Administration", "CS503", 4), ("Software Testing & Quality Assurance", "CS504", 4)],
    6: [("Data Science", "CS601", 4), ("Cloud Computing", "CS602", 4),
        ("Ethical Hacking", "CS603", 4), ("Digital Image Processing", "CS604", 4)],
}

subjects_by_code = {}
for sem, subs in subjects_by_sem.items():
    for name, code, credits in subs:
        subj, _ = Subject.objects.get_or_create(
            subject_code=code, defaults=dict(subject_name=name, credits=credits)
        )
        subjects_by_code[code] = subj
        BranchSubject.objects.get_or_create(branch=branch, subject=subj, semester=sem, defaults=dict(status=1))
        for short, info in classes.items():
            if sem in info["semesters"]:
                SubjectCombination.objects.get_or_create(student_class=info["obj"], subject=subj)

# ── Pan-India name pools (mixed regions: Maharashtrian, Punjabi, South
#    Indian, Bengali, Gujarati, North Indian, etc.) ───────────────────
male_first = [
    "Aarav", "Aditya", "Rohan", "Sanket", "Prathamesh", "Omkar", "Nikhil", "Shubham",
    "Rushikesh", "Tejas", "Akshay", "Vishal", "Suraj", "Yash", "Sarthak", "Abhishek",
    "Pratik", "Amol", "Sagar", "Mahesh", "Ganesh", "Rahul", "Kunal", "Vaibhav",
    "Arjun", "Karan", "Harpreet", "Gurpreet", "Manpreet", "Jaspreet", "Ravinder",
    "Vikram", "Rajesh", "Sandeep", "Amit", "Ankit", "Deepak", "Manish", "Rohit",
    "Venkatesh", "Karthik", "Arun", "Suresh", "Ramesh", "Naveen", "Praveen",
    "Srinivas", "Vijay", "Anand", "Rajat", "Aniket", "Farhan", "Imran", "Zubair",
    "Sourav", "Abir", "Debashish", "Rituraj", "Anupam", "Parth", "Meet", "Jay",
]
female_first = [
    "Sneha", "Pooja", "Priya", "Aishwarya", "Sanika", "Rutuja", "Snehal", "Komal",
    "Shraddha", "Neha", "Vaishnavi", "Anjali", "Pallavi", "Ketaki", "Sayali", "Manasi",
    "Simran", "Harleen", "Jaspreet", "Kirandeep", "Navneet",
    "Divya", "Lakshmi", "Meera", "Priyanka", "Swathi", "Deepika", "Kavya", "Anitha",
    "Sushmita", "Ritika", "Payal", "Kritika", "Isha", "Nidhi", "Shreya",
    "Sohini", "Ananya", "Debolina", "Ishita", "Riya",
    "Foram", "Krisha", "Dhriti", "Heena", "Bhavna",
    "Fatima", "Ayesha", "Zara", "Nazia",
]
surnames = [
    "Deshmukh", "Patil", "Jadhav", "Kulkarni", "Shinde", "Pawar", "More", "Joshi",
    "Chavan", "Gaikwad", "Bhosale", "Sawant", "Kadam", "Salunkhe", "Mane",
    "Singh", "Kaur", "Sharma", "Verma", "Gupta", "Mehra", "Chopra", "Malhotra",
    "Kumar", "Yadav", "Mishra", "Tiwari", "Pandey", "Agarwal", "Jain",
    "Reddy", "Rao", "Naidu", "Iyer", "Iyengar", "Nair", "Menon", "Pillai",
    "Krishnan", "Subramaniam",
    "Banerjee", "Chatterjee", "Mukherjee", "Ghosh", "Das", "Sen", "Bose",
    "Shah", "Patel", "Mehta", "Desai", "Trivedi",
    "Khan", "Ansari", "Siddiqui",
]

def generate_students(n, class_short, start_roll):
    used_names = set()
    combos = []
    while len(combos) < n:
        is_male = len(combos) % 2 == 0
        first = random.choice(male_first if is_male else female_first)
        last = random.choice(surnames)
        full = f"{first} {last}"
        if full in used_names:
            continue
        used_names.add(full)
        combos.append((full, "male" if is_male else "female"))

    created = []
    cls_obj = classes[class_short]["obj"]
    for i, (full_name, gender) in enumerate(combos):
        roll = f"{class_short}{start_roll + i:03d}"
        email = f"{full_name.lower().replace(' ', '.')}.{class_short.lower()}{start_roll+i:03d}@srmscollege.edu.in"
        year_born = {"FYCS": 2006, "SYCS": 2005, "TYCS": 2004}[class_short]
        dob = f"{year_born}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        student, _ = Student.objects.get_or_create(
            roll_id=roll,
            defaults=dict(name=full_name, email=email, gender=gender, dob=dob, student_class=cls_obj, status=1),
        )
        created.append(student)
    return created

all_students = {}
for short in classes:
    all_students[short] = generate_students(50, short, start_roll=1)
    print(f"Created/verified {len(all_students[short])} students for {short}")

def random_marks():
    roll = random.random()
    if roll < 0.08:
        theory = random.randint(5, 11); internal = random.randint(8, 20)
    elif roll < 0.20:
        theory = random.randint(12, 16); internal = random.randint(8, 12)
    else:
        theory = random.randint(17, 30); internal = random.randint(12, 20)
    return theory, internal

result_count = 0
for short, info in classes.items():
    sems = info["semesters"]
    sem_subjects = [s for sem in sems for s in subjects_by_sem[sem]]
    for student in all_students[short]:
        for name, code, credits in sem_subjects:
            subj = subjects_by_code[code]
            theory, internal = random_marks()
            Result.objects.update_or_create(
                student=student, subject=subj,
                defaults=dict(student_class=info["obj"], theory_marks=theory, internal_marks=internal),
            )
            result_count += 1

print(f"Created/updated {result_count} result rows across FYCS/SYCS/TYCS.")
print("=== Done. Log in as admin and check manage_students / manage_result / admin_analytics. ===")
