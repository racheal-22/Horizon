from django.core.management.base import BaseCommand
from django.db import connections

from app.models import (
    School,
    AcademicYear,
    Class,
    Division,
    Subject,
    Teacher,
    StudentEnrollment,
    AttendanceSession,
    StudentAttendance,
    TeacherAttendance
)

class Command(BaseCommand):

    help = "Attendance Sync"

    BATCH_SIZE = 1000

    # ==========================================
    # FETCH MYSQL DATA
    # ==========================================

    def fetch_in_chunks(self, query):

        connection = connections["mysql"]

        cursor = connection.cursor()

        cursor.execute(query)

        columns = [col[0] for col in cursor.description]

        while True:

            rows = cursor.fetchmany(self.BATCH_SIZE)

            if not rows:
                break

            yield [
                dict(zip(columns, row))
                for row in rows
            ]

        cursor.close()

    # ==========================================
    # ATTENDANCE SESSION
    # ==========================================

    def sync_attendance_sessions(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting attendance sessions sync..."
            )
        )

        query = """
            SELECT
                class_id,
                section_id,
                subject_id,
                teacher_id,
                only_date,
                academic_yr,

                COUNT(student_id) as total_students,

                SUM(attendance_status='0') as total_present,

                SUM(attendance_status='1') as total_absent

            FROM attendance

            GROUP BY
                class_id,
                section_id,
                subject_id,
                teacher_id,
                only_date,
                academic_yr
        """

        class_map = {
            c.source_class_id: c
            for c in Class.objects.filter(
                school=school_obj
            )
        }

        division_map = {
            d.source_section_id: d
            for d in Division.objects.filter(
                class_ref__school=school_obj
            )
        }

        subject_map = {
            s.source_subject_id: s
            for s in Subject.objects.filter(
                school=school_obj
            )
        }

        teacher_map = {
            t.teacher_id: t
            for t in Teacher.objects.filter(
                school=school_obj
            )
        }

        academic_year_map = {
            a.name: a
            for a in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        existing_sessions = {

            (
                s.class_ref_id,
                s.division_id,
                s.subject_id,
                s.teacher_id,
                s.date
            ): s

            for s in AttendanceSession.objects.all()
        }

        for chunk in self.fetch_in_chunks(query):

            sessions_to_create = []

            for row in chunk:

                class_obj = class_map.get(
                    row["class_id"]
                )

                division_obj = division_map.get(
                    row["section_id"]
                )

                subject_obj = subject_map.get(
                    row["subject_id"]
                )

                teacher_obj = teacher_map.get(
                    row["teacher_id"]
                )

                academic_year_obj = academic_year_map.get(
                    row["academic_yr"]
                )

                if not class_obj or not division_obj:
                    continue

                key = (
                    class_obj.id if class_obj else None,
                    division_obj.id if division_obj else None,
                    subject_obj.id if subject_obj else None,
                    teacher_obj.id if teacher_obj else None,
                    row["only_date"]
                )

                if key in existing_sessions:
                    continue

                total_students = row["total_students"] or 0
                total_present = row["total_present"] or 0
                total_absent = row["total_absent"] or 0

                attendance_percentage = 0

                if total_students > 0:

                    attendance_percentage = round(
                        (total_present / total_students) * 100,
                        2
                    )

                sessions_to_create.append(

                    AttendanceSession(

                        class_ref=class_obj,

                        division=division_obj,

                        subject=subject_obj,

                        teacher=teacher_obj,

                        academic_year=academic_year_obj,

                        date=row["only_date"],

                        total_students=total_students,

                        total_present=total_present,

                        total_absent=total_absent,

                        attendance_percentage=attendance_percentage
                    )
                )

            if sessions_to_create:

                AttendanceSession.objects.bulk_create(
                    sessions_to_create,
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Attendance sessions sync completed"
            )
        )

    # ==========================================
    # STUDENT ATTENDANCE
    # ==========================================

    def sync_student_attendance(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting student attendance sync..."
            )
        )

        query = """
            SELECT
                student_id,
                class_id,
                section_id,
                subject_id,
                teacher_id,
                only_date,
                academic_yr,
                attendance_status
            FROM attendance
        """

        enrollment_map = {

            (
                int(se.student.unique_user_id),
                se.academic_year.name
            ): se

            for se in StudentEnrollment.objects.filter(
                student__school=school_obj
            )
        }

        session_map = {

            (
                s.class_ref.source_class_id if s.class_ref else None,
                s.division.source_section_id if s.division else None,
                s.subject.source_subject_id if s.subject else None,
                s.teacher.teacher_id if s.teacher else None,
                s.date
            ): s

            for s in AttendanceSession.objects.select_related(
                "class_ref",
                "division",
                "subject",
                "teacher"
            )
        }

        existing_student_attendance = {

            (
                sa.session.id,
                sa.student_enrollment.id
            ): sa

            for sa in StudentAttendance.objects.select_related(
                "session",
                "student_enrollment"
            )
        }

        for chunk in self.fetch_in_chunks(query):

            attendance_to_create = []

            for row in chunk:

                enrollment_obj = enrollment_map.get(

                    (
                        row["student_id"],
                        row["academic_yr"]
                    )
                )

                session_obj = session_map.get(

                    (
                        row["class_id"],
                        row["section_id"],
                        row["subject_id"],
                        row["teacher_id"],
                        row["only_date"]
                    )
                )

                if not enrollment_obj or not session_obj:
                    continue

                key = (
                    session_obj.id,
                    enrollment_obj.id
                )

                if key in existing_student_attendance:
                    continue

                is_present = (
                    row["attendance_status"] == "0"
                )

                attendance_to_create.append(

                    StudentAttendance(

                        session=session_obj,

                        student_enrollment=enrollment_obj,

                        status="Present" if is_present else "Absent",

                        is_present=is_present
                    )
                )

            if attendance_to_create:

                StudentAttendance.objects.bulk_create(
                    attendance_to_create,
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Student attendance sync completed"
            )
        )

    # ==========================================
    # TEACHER ATTENDANCE
    # ==========================================

    def sync_teacher_attendance(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting teacher attendance sync..."
            )
        )

        existing_teacher_attendance = {

            (
                ta.teacher_id,
                ta.date
            ): ta

            for ta in TeacherAttendance.objects.all()
        }

        attendance_to_create = []

        for teacher in Teacher.objects.filter(
            school=school_obj
        ):

            sessions = AttendanceSession.objects.filter(
                teacher=teacher
            )

            grouped_dates = {}

            for session in sessions:

                if session.date not in grouped_dates:

                    grouped_dates[
                        session.date
                    ] = session

            for date, session in grouped_dates.items():

                key = (
                    teacher.id,
                    date
                )

                if key in existing_teacher_attendance:
                    continue

                attendance_to_create.append(

                    TeacherAttendance(

                        teacher=teacher,

                        date=date,

                        punch_time=None,

                        is_present=True
                    )
                )

        if attendance_to_create:

            TeacherAttendance.objects.bulk_create(
                attendance_to_create,
                batch_size=self.BATCH_SIZE
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Teacher attendance sync completed"
            )
        )

    # ==========================================
    # HANDLE
    # ==========================================

    def handle(self, *args, **kwargs):

        school_obj = School.objects.first()

        if not school_obj:

            self.stdout.write(
                self.style.ERROR(
                    "No school found"
                )
            )

            return

        self.sync_attendance_sessions(
            school_obj
        )

        self.sync_student_attendance(
            school_obj
        )

        self.sync_teacher_attendance(
            school_obj
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Attendance sync completed successfully"
            )
        )