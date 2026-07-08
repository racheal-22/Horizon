from django.core.management.base import BaseCommand
from django.db.models import Avg, Count

from app.models import (
    School,
    StudentEnrollment,
    Mark,
    StudentAttendance,
    StudentAchievement,
    HomeworkSubmission,
    BookIssue,
    ParentFeedback,
    StudentYearSummary,
    StudentBehaviorAnalysis
)


class Command(BaseCommand):

    help = "Generate Analytics + Behaviour Data"

    # =====================================
    # STUDENT YEAR SUMMARY
    # =====================================

    def generate_student_summary(self):

        StudentYearSummary.objects.all().delete()

        summaries_to_create = []

        enrollments = StudentEnrollment.objects.select_related(
            "student",
            "academic_year",
            "school"
        )

        for enrollment in enrollments:

            avg_marks = Mark.objects.filter(
                student_enrollment=enrollment
            ).aggregate(
                avg=Avg("percentage")
            )["avg"] or 0

            attendance = StudentAttendance.objects.filter(
                student_enrollment=enrollment
            ).aggregate(
                avg=Avg("attendance_percentage")
            )["avg"] or 0

            achievement = StudentAchievement.objects.filter(
                student=enrollment.student,
                academic_year=enrollment.academic_year
            ).first()

            summaries_to_create.append(

                StudentYearSummary(
                    school=enrollment.school,

                    student_enrollment=enrollment,

                    avg_marks=round(
                        avg_marks,
                        2
                    ),

                    attendance_percentage=round(
                        attendance,
                        2
                    ),

                    achievement_id=
                    achievement.id if achievement else 0

                )
            )

        if summaries_to_create:

            StudentYearSummary.objects.bulk_create(
                summaries_to_create,
                batch_size=1000
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Student summary generated"
            )
        )

    # =====================================
    # STUDENT BEHAVIOUR ANALYSIS
    # =====================================

    def generate_behavior_analysis(
        self,
        school_obj
    ):

        StudentBehaviorAnalysis.objects.filter(
            school=school_obj
        ).delete()

        enrollments = StudentEnrollment.objects.select_related(
            "student",
            "academic_year"
        ).filter(
            school=school_obj
        )

        for enrollment in enrollments:

            attendance = StudentAttendance.objects.filter(
                school=school_obj,
                student_enrollment=enrollment
            ).aggregate(
                avg=Avg("attendance_percentage")
            )["avg"] or 0

            homework_on_time = HomeworkSubmission.objects.filter(
                school=school_obj,
                student_enrollment=enrollment,
                status="Submitted"
            ).count()

            assignments_pending = HomeworkSubmission.objects.filter(
                school=school_obj,
                student_enrollment=enrollment,
                status="Pending"
            ).count()

            books_returned = BookIssue.objects.filter(
                school=school_obj,
                student=enrollment.student,
                status="Returned"
            ).count()

            parent_feedback_avg = ParentFeedback.objects.filter(
                school=school_obj,
                student=enrollment.student,
                academic_year=enrollment.academic_year
            ).aggregate(
                avg=Avg("rating")
            )["avg"] or 3

            complaints_count = max(
                0,
                5 - int(parent_feedback_avg)
            )

            participation_score = (
                homework_on_time * 2
            ) + (
                books_returned * 2
            )

            overall_score = (
                float(attendance) * 0.4
            ) + (
                participation_score * 0.3
            ) + (
                float(parent_feedback_avg) * 10 * 0.3
            )

            remarks = "Excellent"

            if overall_score < 40:
                remarks = "Needs Improvement"

            elif overall_score < 70:
                remarks = "Average"

            StudentBehaviorAnalysis.objects.create(

                school=school_obj,

                student_enrollment=enrollment,

                academic_year=enrollment.academic_year,

                complaints_count=complaints_count,

                remarks=remarks,

                event_participation_score=round(
                    participation_score,
                    2
                ),

                books_returned_on_time=books_returned,

                homework_on_time=homework_on_time,

                assignments_on_time=homework_on_time,

                attendance_percentage=round(
                    attendance,
                    2
                ),

                overall_behavior_score=round(
                    overall_score,
                    2
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Behavior analysis generated for {school_obj}"
            )
        )

    # =====================================
    # HANDLE
    # =====================================

    def handle(self, *args, **kwargs):

        self.generate_student_summary()

        # Only run behavior analysis for schools that actually
        # have enrollments, instead of every School row.
        school_ids = (
            StudentEnrollment.objects
            .values_list("school_id", flat=True)
            .distinct()
        )

        schools = School.objects.filter(id__in=school_ids)

        if not schools.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No schools with enrollments found; "
                    "skipping behavior analysis."
                )
            )

        for school_obj in schools:
            self.generate_behavior_analysis(school_obj)

        self.stdout.write(
            self.style.SUCCESS(
                "Analytics generated successfully"
            )
        )