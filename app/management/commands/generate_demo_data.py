from django.core.management.base import BaseCommand
from faker import Faker
import random

from app.models import (
    Homework,
    HomeworkSubmission,
    RemedialSession,
    StudentAchievement,
    TeacherAchievement,
    StudentHealthRecord,
    Project,
    TeacherActiveness,
    ParentFeedback,
    Subject,
    StudentEnrollment,
    Teacher,
    Student,
    School,
)

fake = Faker()


class Command(BaseCommand):

    help = "Generate Demo Analytics Data"

    # =====================================
    # HOMEWORK
    # =====================================
    def generate_homework(self, school_obj):

        homework_titles = [
            "Math Worksheet",
            "Science Diagram",
            "English Essay",
            "Grammar Practice",
            "Physics Numericals",
            "Chemistry Notes",
            "Computer Coding Task"
        ]

        subjects = Subject.objects.select_related(
            "division",
            "academic_year"
        ).filter(
            school=school_obj
        )

        homework_count = 0
        submission_count = 0

        for subject in subjects:

            if not subject.teacher_id:
                continue

            enrollments = StudentEnrollment.objects.filter(
                school=school_obj,
                division=subject.division,
                academic_year=subject.academic_year
            )

            if not enrollments.exists():
                continue

            self.stdout.write(
                f"Generating homework for {subject}"
            )

            for _ in range(random.randint(2, 5)):

                homework = Homework.objects.create(

                    school=school_obj,

                    division=subject.division,

                    subject=subject,

                    teacher_id=subject.teacher_id,

                    academic_year=subject.academic_year,

                    title=random.choice(homework_titles),

                    description=fake.paragraph(),

                    due_date=fake.date_between(
                        start_date="-60d",
                        end_date="+15d"
                    ),

                    status="Assigned"
                )

                homework_count += 1

                submissions = []

                for enrollment in enrollments:

                    status = random.choices(
                        ["Submitted", "Late", "Pending"],
                        weights=[75, 15, 10]
                    )[0]

                    submissions.append(

                        HomeworkSubmission(

                            school=school_obj,

                            homework=homework,

                            student_enrollment=enrollment,

                            status=status
                        )
                    )

                    submission_count += 1

                HomeworkSubmission.objects.bulk_create(
                    submissions
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"{homework_count} homework generated"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{submission_count} submissions generated"
            )
        )
    # =====================================
    # REMEDIAL
    # =====================================
    def generate_remedial(self, school_obj):

        remedial_notes = [
            "Needs grammar improvement",
            "Weak in calculations",
            "Concept clarity required",
            "Reading practice needed",
            "Extra assignments given"
        ]

        remedial_count = 0

        enrollments = StudentEnrollment.objects.select_related(
            "division",
            "academic_year"
        ).filter(
            school=school_obj
        )

        for enrollment in enrollments:

            pending_homework = HomeworkSubmission.objects.filter(
                school=school_obj,
                student_enrollment=enrollment,
                status="Pending"
            ).exists()

            if not pending_homework:
                continue

            create_data = random.choices(
                [True, False],
                weights=[10, 90]
            )[0]

            if not create_data:
                continue

            subjects = Subject.objects.filter(
                school=school_obj,
                division=enrollment.division,
                academic_year=enrollment.academic_year
            )

            if not subjects.exists():
                continue

            subject = random.choice(subjects)

            if not subject.teacher_id:
                continue

            RemedialSession.objects.create(

                school=school_obj,

                student_enrollment=enrollment,

                academic_year=enrollment.academic_year,

                subject=subject,

                teacher_id=subject.teacher_id,

                session_date=fake.date_between(
                    start_date="-90d",
                    end_date="today"
                ),

                notes=random.choice(
                    remedial_notes
                )
            )

            remedial_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{remedial_count} remedial sessions generated"
            )
        )
    # =====================================
    # STUDENT ACHIEVEMENTS
    # =====================================
    def generate_student_achievements(self, school_obj):

        titles = [
            "Science Olympiad Winner",
            "Football Champion",
            "Coding Competition Winner",
            "Chess Champion",
            "Debate Finalist",
            "Best Student Award"
        ]

        count = 0

        students = Student.objects.filter(
            school=school_obj
        )

        for student in students:

            create_data = random.choices(
                [True, False],
                weights=[35, 65]
            )[0]

            if not create_data:
                continue

            enrollment = StudentEnrollment.objects.filter(
                school=school_obj,
                student=student
            ).first()

            if not enrollment:
                continue

            StudentAchievement.objects.create(

                school=school_obj,

                student=student,

                academic_year=enrollment.academic_year,

                title=random.choice(titles),

                type=random.choice([
                    "Academic",
                    "Sports",
                    "Technology",
                    "Cultural"
                ]),

                description=fake.paragraph(),

                date=fake.date_between(
                    start_date="-365d",
                    end_date="today"
                )
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} student achievements generated"
            )
        )
    # =====================================
    # TEACHER ACHIEVEMENTS
    # =====================================

    def generate_teacher_achievements(self, school_obj):

        titles = [
            "Best Teacher Award",
            "Outstanding Mentor",
            "Innovation in Teaching",
            "Leadership Excellence"
        ]

        count = 0

        teachers = Teacher.objects.filter(
            school=school_obj
        )

        for teacher in teachers:

            create_data = random.choices(
                [True, False],
                weights=[40, 60]
            )[0]

            if not create_data:
                continue

            TeacherAchievement.objects.create(

                school=school_obj,

                teacher_id=teacher.id,

                title=random.choice(
                    titles
                ),

                description=fake.paragraph(),

                date=fake.date_between(
                    start_date="-730d",
                    end_date="today"
                )
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} teacher achievements generated"
            )
        )
    # =====================================
    # HEALTH
    # =====================================
    def generate_health_records(self, school_obj):

        count = 0

        students = Student.objects.filter(
            school=school_obj
        )

        for student in students:

            for _ in range(2):

                StudentHealthRecord.objects.create(

                    school=school_obj,

                    student=student,

                    height=round(
                        random.uniform(120, 180),
                        2
                    ),

                    weight=round(
                        random.uniform(25, 80),
                        2
                    ),

                    recorded_date=fake.date_between(
                        start_date="-365d",
                        end_date="today"
                    )
                )

                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} health records generated"
            )
        )
    # =====================================
    # PROJECTS
    # =====================================
    def generate_projects(self, school_obj):

        titles = [
            "AI Chatbot",
            "Solar System Model",
            "Smart Irrigation",
            "Robotics Project",
            "Science Exhibition"
        ]

        count = 0

        students = Student.objects.filter(
            school=school_obj
        )

        for student in students:

            create_data = random.choices(
                [True, False],
                weights=[45, 55]
            )[0]

            if not create_data:
                continue

            Project.objects.create(

                school=school_obj,

                student=student,

                title=random.choice(
                    titles
                ),

                description=fake.paragraph(),

                date=fake.date_between(
                    start_date="-365d",
                    end_date="today"
                ),

                type=random.choice([
                    "Science",
                    "Technology",
                    "School",
                    "Home"
                ])
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} projects generated"
            )
        )
    # =====================================
    # TEACHER ACTIVENESS
    # =====================================
    def generate_teacher_activeness(self, school_obj):

        events = [
            "Annual Day",
            "Sports Day",
            "Science Exhibition",
            "Workshop",
            "PTM",
            "Exam Duty"
        ]

        count = 0

        subjects = Subject.objects.select_related(
            "division",
            "class_ref",
            "academic_year"
        ).filter(
            school=school_obj
        )

        for subject in subjects:

            if not subject.teacher_id:
                continue

            for _ in range(random.randint(1, 3)):

                TeacherActiveness.objects.create(

                    school=school_obj,

                    teacher_id=subject.teacher_id,

                    class_ref=subject.class_ref,

                    division=subject.division,

                    academic_year=subject.academic_year,

                    event_name=random.choice(
                        events
                    ),

                    event_type=random.choice([
                        "Academic",
                        "Sports",
                        "Management",
                        "Cultural"
                    ]),

                    assigned_date=fake.date_between(
                        start_date="-365d",
                        end_date="today"
                    ),

                    status=random.choice([
                        "Completed",
                        "Assigned",
                        "Pending"
                    ])
                )

                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} teacher activeness generated"
            )
        )
    # =====================================
    # PARENT FEEDBACK
    # =====================================
    def generate_parent_feedback(self, school_obj):

        feedbacks = [
            "Very supportive teacher",
            "Excellent teaching methods",
            "Good improvement in child",
            "Homework tracking is good",
            "Needs more attention"
        ]

        count = 0

        enrollments = StudentEnrollment.objects.select_related(
            "student",
            "division",
            "academic_year"
        ).filter(
            school=school_obj
        )

        for enrollment in enrollments:

            student = enrollment.student

            if not student.parent:
                continue

            subjects = Subject.objects.filter(
                school=school_obj,
                division=enrollment.division,
                academic_year=enrollment.academic_year
            )

            if not subjects.exists():
                continue

            subject = random.choice(subjects)

            if not subject.teacher_id:
                continue

            ParentFeedback.objects.create(

                school=school_obj,

                parent=student.parent,

                teacher_id=subject.teacher_id,

                student=student,

                academic_year=enrollment.academic_year,

                feedback_text=random.choice(
                    feedbacks
                ),

                rating=random.randint(3, 5)
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} parent feedback generated"
            )
        )

    # =====================================
    # HANDLE
    # =====================================
    def handle(self, *args, **kwargs):

        school_obj = School.objects.first()

        if not school_obj:

            self.stdout.write(
                self.style.ERROR(
                    "No school found"
                )
            )

            return

        self.stdout.write("Deleting old demo data...")

        HomeworkSubmission.objects.filter(
            school=school_obj
        ).delete()

        Homework.objects.filter(
            school=school_obj
        ).delete()

        RemedialSession.objects.filter(
            school=school_obj
        ).delete()

        StudentAchievement.objects.filter(
            school=school_obj
        ).delete()

        TeacherAchievement.objects.filter(
            school=school_obj
        ).delete()

        StudentHealthRecord.objects.filter(
            school=school_obj
        ).delete()

        Project.objects.filter(
            school=school_obj
        ).delete()

        TeacherActiveness.objects.filter(
            school=school_obj
        ).delete()

        ParentFeedback.objects.filter(
            school=school_obj
        ).delete()

        self.stdout.write("Old data deleted")

        self.generate_homework(school_obj)

        self.generate_remedial(school_obj)

        self.generate_student_achievements(
            school_obj
        )

        self.generate_teacher_achievements(
            school_obj
        )

        self.generate_health_records(
            school_obj
        )

        self.generate_projects(
            school_obj
        )

        self.generate_teacher_activeness(
            school_obj
        )

        self.generate_parent_feedback(
            school_obj
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo analytics data generated successfully"
            )
        )