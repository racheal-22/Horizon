from django.core.management.base import BaseCommand
from django.db import connections

from app.models import (
    AttendanceSession,
    School,
    AcademicYear,
    User,
    SyncTracker,    ExamType,
    Exam,
    ExamSubject,
    Mark,
    StudentAttendance,
    TeacherAttendance,
    Parent, Department, Class, Division, DepartmentSpecialRole, Student, StudentEnrollment,Teacher,Subject,SubjectMaster,SubjectReportCard,SubjectReportCardMaster,

)



class Command(BaseCommand):

    help = "Library Sync"

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

            rows = cursor.fetchmany(
                self.BATCH_SIZE
            )

            if not rows:
                break

            yield [
                dict(zip(columns, row))
                for row in rows
            ]

        cursor.close()


    def sync_subject_master(self,school_obj):

        query="""
            SELECT
            sm_id,
            name,
            subject_type
            FROM subject_master
        """

        existing_subjects={
            s.source_sm_id:s
            for s in SubjectMaster.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            subjects_to_create=[]
            subjects_to_update=[]

            for row in chunk:

                existing_subject=existing_subjects.get(
                    row["sm_id"]
                )

                if existing_subject:

                    existing_subject.school=school_obj

                    existing_subject.name=row["name"]

                    existing_subject.subject_type=row[
                        "subject_type"
                    ]

                    subjects_to_update.append(
                        existing_subject
                    )

                else:

                    subject_obj=SubjectMaster(

                        school=school_obj,

                        source_sm_id=row["sm_id"],

                        name=row["name"],

                        subject_type=row[
                            "subject_type"
                        ]

                    )

                    subjects_to_create.append(
                        subject_obj
                    )

                    existing_subjects[
                        row["sm_id"]
                    ] = True

            if subjects_to_create:

                SubjectMaster.objects.bulk_create(
                    subjects_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if subjects_to_update:

                SubjectMaster.objects.bulk_update(
                    subjects_to_update,
                    [
                        
                        "name",
                        "subject_type"
                    ],
                    batch_size=self.BATCH_SIZE
                )

            

    def sync_subjects(self,school_obj):

        query="""
            SELECT
            subject_id,
            sm_id,
            class_id,
            section_id,
            teacher_id,
            academic_yr,
            created_at,
            updated_at
            FROM subject
        """

        subject_master_map={
            s.source_sm_id:s
            for s in SubjectMaster.objects.filter(
                school=school_obj
            )
        }

        class_map={
            c.source_class_id:c
            for c in Class.objects.filter(
                school=school_obj
            )
        }

        division_map={
            d.source_section_id:d
            for d in Division.objects.filter(
                school=school_obj
            )
        }

        teacher_map={
            t.teacher_id:t
            for t in Teacher.objects.filter(
                school=school_obj
            )
        }

        academic_year_map={
            a.name:a
            for a in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        existing_subjects={
            s.source_subject_id:s
            for s in Subject.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            subjects_to_create=[]
            subjects_to_update=[]

            for row in chunk:

                subject_master_obj=subject_master_map.get(
                    row["sm_id"]
                )

                if subject_master_obj is None:
                    self.log_sync(
                        school=school_obj,
                        source_table="subject",
                        source_primary_id=row["subject_id"],
                        target_table="subject",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=f"SubjectMaster not found for sm_id={row['sm_id']}"
                    )
                    continue

                class_obj=class_map.get(
                    row["class_id"]
                )

                division_obj=division_map.get(
                    row["section_id"]
                )

                teacher_obj=teacher_map.get(
                    row["teacher_id"]
                )

                academic_year_obj=academic_year_map.get(
                    row["academic_yr"]
                )

                existing_subject=existing_subjects.get(
                    row["subject_id"]
                )

                if existing_subject:

                    existing_subject.school=school_obj

                    existing_subject.subject_master=subject_master_obj

                    existing_subject.class_ref=class_obj

                    existing_subject.division=division_obj

                    existing_subject.teacher=teacher_obj

                    existing_subject.academic_year=academic_year_obj

                    existing_subject.created_at=row[
                        "created_at"
                    ]

                    existing_subject.updated_at=row[
                        "updated_at"
                    ]

                    subjects_to_update.append(
                        existing_subject
                    )

                else:

                    subject_obj=Subject(

                        school=school_obj,

                        source_subject_id=row[
                            "subject_id"
                        ],

                        subject_master=subject_master_obj,

                        class_ref=class_obj,

                        division=division_obj,

                        teacher=teacher_obj,

                        academic_year=academic_year_obj,

                        created_at=row[
                            "created_at"
                        ],

                        updated_at=row[
                            "updated_at"
                        ]

                    )

                    subjects_to_create.append(
                        subject_obj
                    )

                    existing_subjects[
                        row["subject_id"]
                    ] = True

            if subjects_to_create:

                Subject.objects.bulk_create(
                    subjects_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if subjects_to_update:

                Subject.objects.bulk_update(
                    subjects_to_update,
                    [
                        
                        "subject_master",
                        "class_ref",
                        "division",
                        "teacher",
                        "academic_year",
                        "created_at",
                        "updated_at"
                    ],
                    batch_size=self.BATCH_SIZE
                )


    def sync_subject_report_card_master(self,school_obj):

        query="""
            SELECT
            sub_rc_master_id,
            name,
            sequence,
            created_at,
            updated_at
            FROM subjects_on_report_card_master
        """

        existing_report_cards={
            s.source_sub_rc_master_id:s
            for s in SubjectReportCardMaster.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            report_cards_to_create=[]
            report_cards_to_update=[]

            for row in chunk:

                existing_report_card=existing_report_cards.get(
                    row["sub_rc_master_id"]
                )

                if existing_report_card:

                    existing_report_card.name=row["name"]

                    existing_report_card.sequence=row["sequence"]

                    existing_report_card.created_at=row[
                        "created_at"
                    ]

                    existing_report_card.updated_at=row[
                        "updated_at"
                    ]

                    report_cards_to_update.append(
                        existing_report_card
                    )

                else:

                    report_card_obj=SubjectReportCardMaster(

                        school=school_obj,

                        source_sub_rc_master_id=row[
                            "sub_rc_master_id"
                        ],

                        name=row["name"],

                        sequence=row["sequence"],

                        created_at=row[
                            "created_at"
                        ],

                        updated_at=row[
                            "updated_at"
                        ]

                    )

                    report_cards_to_create.append(
                        report_card_obj
                    )

                    # Prevent duplicate inserts in same run

                    existing_report_cards[
                        row["sub_rc_master_id"]
                    ] = True

            if report_cards_to_create:

                SubjectReportCardMaster.objects.bulk_create(
                    report_cards_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if report_cards_to_update:

                SubjectReportCardMaster.objects.bulk_update(
                    report_cards_to_update,
                    [
                        "name",
                        "sequence",
                        "created_at",
                        "updated_at"
                    ],
                    batch_size=self.BATCH_SIZE
                )
    

    def sync_subject_report_cards(self,school_obj):

        query="""
            SELECT
            sub_reportcard_id,
            sub_rc_master_id,
            class_id,
            subject_type,
            academic_yr,
            created_at,
            updated_at
            FROM subjects_on_report_card
        """

        report_card_master_map={
            s.source_sub_rc_master_id:s
            for s in SubjectReportCardMaster.objects.filter(
                school=school_obj
            )
        }

        class_map={
            c.source_class_id:c
            for c in Class.objects.filter(
                school=school_obj
            )
        }

        academic_year_map={
            a.name:a
            for a in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        existing_report_cards={
            s.source_sub_reportcard_id:s
            for s in SubjectReportCard.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            report_cards_to_create=[]
            report_cards_to_update=[]

            for row in chunk:

                report_card_master_obj=report_card_master_map.get(
                    row["sub_rc_master_id"]
                )

                class_obj=class_map.get(
                    row["class_id"]
                )

                academic_year_obj=academic_year_map.get(
                    row["academic_yr"]
                )

                if not report_card_master_obj \
                or not class_obj \
                or not academic_year_obj:
                    continue

                existing_report_card=existing_report_cards.get(
                    row["sub_reportcard_id"]
                )

                if existing_report_card:

                    existing_report_card.report_card_master=(
                        report_card_master_obj
                    )

                    existing_report_card.class_ref=class_obj

                    existing_report_card.subject_type=row[
                        "subject_type"
                    ]

                    existing_report_card.academic_year=(
                        academic_year_obj
                    )

                    existing_report_card.created_at=row[
                        "created_at"
                    ]

                    existing_report_card.updated_at=row[
                        "updated_at"
                    ]

                    report_cards_to_update.append(
                        existing_report_card
                    )

                else:

                    report_card_obj=SubjectReportCard(

                        school=school_obj,

                        source_sub_reportcard_id=row[
                            "sub_reportcard_id"
                        ],

                        report_card_master=
                        report_card_master_obj,

                        class_ref=class_obj,

                        subject_type=row[
                            "subject_type"
                        ],

                        academic_year=
                        academic_year_obj,

                        created_at=row[
                            "created_at"
                        ],

                        updated_at=row[
                            "updated_at"
                        ]

                    )

                    report_cards_to_create.append(
                        report_card_obj
                    )

                    existing_report_cards[
                        row["sub_reportcard_id"]
                    ] = True

            if report_cards_to_create:

                SubjectReportCard.objects.bulk_create(
                    report_cards_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if report_cards_to_update:

                SubjectReportCard.objects.bulk_update(
                    report_cards_to_update,
                    [
                        "report_card_master",
                        "class_ref",
                        "subject_type",
                        "academic_year",
                        "created_at",
                        "updated_at"
                    ],
                    batch_size=self.BATCH_SIZE
                )

    def sync_exam_types(self, school_obj):

        query = """
            SELECT
            marks_headings_id,
            name
            FROM marks_headings
        """

        existing_exam_types = {
            e.source_exam_type_id: e
            for e in ExamType.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            exam_types_to_create = []

            for row in chunk:

                if row["marks_headings_id"] not in existing_exam_types:

                    exam_types_to_create.append(

                        ExamType(

                            school=school_obj,

                            source_exam_type_id=row[
                                "marks_headings_id"
                            ],

                            name=row["name"],

                            weightage=0

                        )
                    )

                existing_exam_types[
                    row["marks_headings_id"]
                ] = True

            if exam_types_to_create:

                ExamType.objects.bulk_create(
                    exam_types_to_create,
                    batch_size=self.BATCH_SIZE
                )

    def sync_exams(self, school_obj):

        query = """
            SELECT
            exam_id,
            name,
            start_date,
            academic_yr
            FROM exam
        """

        academic_year_map = {
            a.name: a
            for a in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        default_exam_type = ExamType.objects.filter(
            school=school_obj
        ).first()

        existing_exams = {
            e.source_exam_id: e
            for e in Exam.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            exams_to_create = []
            exams_to_update = []

            for row in chunk:

                academic_year_obj = academic_year_map.get(
                    row["academic_yr"]
                )

                if not academic_year_obj:
                    continue

                existing_exam = existing_exams.get(
                    row["exam_id"]
                )

                if existing_exam:

                    existing_exam.academic_year = (
                        academic_year_obj
                    )

                    existing_exam.exam_type = (
                        default_exam_type
                    )

                    existing_exam.name = row["name"]

                    existing_exam.start_date = (
                        row["start_date"]
                    )

                    exams_to_update.append(
                        existing_exam
                    )

                else:

                    exam_obj = Exam(

                        school=school_obj,

                        source_exam_id=row["exam_id"],

                        academic_year=academic_year_obj,

                        exam_type=default_exam_type,

                        name=row["name"],

                        start_date=row["start_date"]

                    )

                    exams_to_create.append(
                        exam_obj
                    )

                    existing_exams[
                        row["exam_id"]
                    ] = True

            if exams_to_create:

                Exam.objects.bulk_create(
                    exams_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if exams_to_update:

                Exam.objects.bulk_update(
                    exams_to_update,
                    [
                        "academic_year",
                        "exam_type",
                        "name",
                        "start_date"
                    ],
                    batch_size=self.BATCH_SIZE
                )
        
        
    def sync_exam_subjects(self, school_obj):

        query = """
            SELECT DISTINCT
            exam_id,
            subject_id,
            highest_total_marks
            FROM student_marks
        """

        school_id = school_obj.id

        exam_map = {
            e.source_exam_id: e
            for e in Exam.objects.filter(
                school_id=school_id
            )
        }

        subject_map = {
            s.source_subject_id: s
            for s in Subject.objects.filter(
                school_id=school_id
            )
        }

        existing_exam_subjects = {

            (
                es.exam_id,
                es.subject_id
            ): es

            for es in ExamSubject.objects.filter(
                school_id=school_id
            )
        }

        for chunk in self.fetch_in_chunks(query):

            exam_subjects_to_create = []

            for row in chunk:

                try:

                    subject_id = int(
                        str(row["subject_id"]).split(",")[0]
                    )

                except:
                    continue

                exam_obj = exam_map.get(
                    row["exam_id"]
                )

                subject_obj = subject_map.get(
                    subject_id
                )

                if not exam_obj or not subject_obj:
                    continue

                key = (
                    exam_obj.id,
                    subject_obj.id
                )

                if key in existing_exam_subjects:
                    continue

                exam_subjects_to_create.append(

                    ExamSubject(

                        school_id=school_id,

                        exam=exam_obj,

                        subject=subject_obj,

                        max_marks=row[
                            "highest_total_marks"
                        ] or 0

                    )
                )

                existing_exam_subjects[
                    key
                ] = True

            if exam_subjects_to_create:

                ExamSubject.objects.bulk_create(
                    exam_subjects_to_create,
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Exam subjects sync completed"
            )
        )

    def sync_marks(self, school_obj):

        query = """
            SELECT
            marks_id,
            class_id,
            section_id,
            exam_id,
            subject_id,
            student_id,
            academic_yr,
            present,
            mark_obtained,
            highest_marks,
            percent
            FROM student_marks
        """

        student_map = {

            (
                int(s.student.unique_user_id),
                s.academic_year.name
            ): s

            for s in StudentEnrollment.objects.filter(
                school=school_obj
            )
        }

        exam_subject_map = {
            (
                es.exam.source_exam_id,
                es.subject.source_subject_id
            ): es

            for es in ExamSubject.objects.select_related(
                "exam",
                "subject"
            ).filter(
                subject__school=school_obj
            )
        }

        exam_type_map = {

            et.name: et

            for et in ExamType.objects.filter(
                school=school_obj
            )
        }

        marks_heading_map = {}

        query2 = """
            SELECT
            marks_headings_id,
            name
            FROM marks_headings
        """

        for chunk2 in self.fetch_in_chunks(query2):

            for row2 in chunk2:

                marks_heading_map[
                    str(row2["marks_headings_id"])
                ] = row2["name"]

        existing_marks = {

            (
                m.student_enrollment.id,
                m.exam_subject.id,
                m.exam_type.id
            ): m

            for m in Mark.objects.select_related(
                "student_enrollment",
                "exam_subject",
                "exam_type"
            ).filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            marks_to_create = []

            for row in chunk:

                try:

                    subject_id = int(
                        str(row["subject_id"]).split(",")[0]
                    )

                except:

                    continue

                enrollment_obj = student_map.get(

                    (
                        row["student_id"],
                        row["academic_yr"]
                    )
                )

                exam_subject_obj = exam_subject_map.get(

                    (
                        row["exam_id"],
                        subject_id
                    )
                )

                if not enrollment_obj or not exam_subject_obj:
                    continue

                try:

                    obtained_data = json.loads(
                        row["mark_obtained"].replace("'", '"')
                    )

                    highest_data = json.loads(
                        row["highest_marks"].replace("'", '"')
                    )

                    raw_percent = str(
                        row["percent"] or ""
                    ).strip()

                    if raw_percent.startswith("{"):

                        percent_data = json.loads(
                            raw_percent.replace("'", '"')
                        )

                    else:

                        try:

                            percent_data = float(
                                raw_percent
                            )

                        except:

                            percent_data = 0

                    present_data = json.loads(
                        row["present"].replace("'", '"')
                    )

                    if not isinstance(
                        obtained_data,
                        dict
                    ):
                        obtained_data = {}

                    if not isinstance(
                        highest_data,
                        dict
                    ):
                        highest_data = {}

                    if not isinstance(
                        present_data,
                        dict
                    ):
                        present_data = {}

                except Exception as e:

                    print(
                        "JSON ERROR :",
                        row["marks_id"],
                        str(e)
                    )

                    print(
                        "mark_obtained:",
                        row["mark_obtained"]
                    )

                    print(
                        "highest_marks:",
                        row["highest_marks"]
                    )

                    print(
                        "percent:",
                        row["percent"]
                    )

                    print(
                        "present:",
                        row["present"]
                    )

                    continue

                  

                for (
                    marks_heading_id,
                    obtained_marks
                ) in obtained_data.items():

                    heading_name = marks_heading_map.get(
                        str(marks_heading_id)
                    )

                    if not heading_name:
                        continue

                    exam_type_obj = exam_type_map.get(
                        heading_name
                    )

                    if not exam_type_obj:
                        continue

                    total_marks = highest_data.get(
                        str(marks_heading_id),
                        0
                    )
                    if isinstance(
                        percent_data,
                        dict
                    ):

                        percentage = percent_data.get(
                            str(marks_heading_id),
                            0
                        )

                    else:

                        percentage = percent_data

                    is_present = present_data.get(
                        str(marks_heading_id),
                        "N"
                    )

                    key = (

                        enrollment_obj.id,

                        exam_subject_obj.id,

                        exam_type_obj.id
                    )

                    if key in existing_marks:
                        continue

                    try:
                        obtained_marks = float(
                            obtained_marks
                        )
                    except:
                        obtained_marks = 0

                    try:
                        total_marks = float(
                            total_marks
                        )
                    except:
                        total_marks = 0

                    try:
                        percentage = float(
                            percentage
                        )
                    except:
                        percentage = 0

                    marks_to_create.append(

                        Mark(

                            school=school_obj,

                            source_mark_id=row[
                                "marks_id"
                            ],

                            student_enrollment=
                            enrollment_obj,

                            exam_subject=
                            exam_subject_obj,

                            exam_type=
                            exam_type_obj,

                            obtained_marks=
                            obtained_marks,

                            total_marks=
                            total_marks,

                            percentage=
                            percentage,

                            is_present=
                            is_present

                        )
                    )
                    existing_marks[key] = True

            if marks_to_create:

                Mark.objects.bulk_create(
                    marks_to_create,
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Marks sync completed"
            )
        )





    def sync_attendance_sessions(self, school_obj):

        query="""
            SELECT

            MIN(attendance_id) as attendance_session_id,

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

        class_map={
            c.source_class_id:c
            for c in Class.objects.filter(
                school=school_obj
            )
        }

        division_map={
            d.source_section_id:d
            for d in Division.objects.filter(
                school=school_obj
            )
        }

        subject_map={
            s.source_subject_id:s
            for s in Subject.objects.filter(
                school=school_obj
            )
        }

        teacher_map={
            t.teacher_id:t
            for t in Teacher.objects.filter(
                school=school_obj
            )
        }

        academic_year_map={
            a.name:a
            for a in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        existing_sessions={

            (
                s.class_ref_id,
                s.division_id,
                s.subject_id,
                s.academic_year_id,
                s.date
            ):s

            for s in AttendanceSession.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            sessions_to_create=[]

            for row in chunk:

                class_obj=class_map.get(
                    row["class_id"]
                )

                division_obj=division_map.get(
                    row["section_id"]
                )

                subject_obj=subject_map.get(
                    row["subject_id"]
                )

                teacher_obj=teacher_map.get(
                    row["teacher_id"]
                )

                academic_year_obj=academic_year_map.get(
                    row["academic_yr"]
                )

                total_students=row["total_students"] or 0

                total_present=row["total_present"] or 0

                total_absent=row["total_absent"] or 0

                attendance_percentage=0

                if total_students>0:

                    attendance_percentage=round(
                        (total_present/total_students)*100,
                        2
                    )

                key=(

                    class_obj.id if class_obj else None,

                    division_obj.id if division_obj else None,

                    subject_obj.id if subject_obj else None,

                    academic_year_obj.id if academic_year_obj else None,

                    row["only_date"]
                )

                if key in existing_sessions:
                    continue

                sessions_to_create.append(

                    AttendanceSession(

                        school=school_obj,

                        source_attendance_session_id=
                        row["attendance_session_id"],

                        class_ref=class_obj,

                        division=division_obj,

                        subject=subject_obj,

                        teacher=teacher_obj,

                        academic_year=academic_year_obj,

                        date=row["only_date"],

                        total_students=total_students,

                        total_present=total_present,

                        total_absent=total_absent,

                        attendance_percentage=
                        attendance_percentage

                    )
                )

                existing_sessions[key] = True

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



    def sync_student_attendance(self,school_obj):

        query="""
            SELECT

            attendance_id,

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

        enrollment_map={

            (
                int(se.student.unique_user_id),
                se.academic_year.name
            ):se

            for se in StudentEnrollment.objects.filter(
                school=school_obj
            )
        }

        session_map={

            (
                s.class_ref.source_class_id if s.class_ref else None,

                s.division.source_section_id if s.division else None,

                s.subject.source_subject_id if s.subject else None,

                s.date

            ):s

            for s in AttendanceSession.objects.filter(
                school=school_obj
            ).select_related(
                "class_ref",
                "division",
                "subject"
            )
        }

        attendance_summary={}

        summary_query="""
            SELECT

            student_id,
            academic_yr,

            COUNT(*) as total_days,

            SUM(attendance_status='0') as present_days,

            SUM(attendance_status='1') as absent_days

            FROM attendance

            GROUP BY
            student_id,
            academic_yr
        """

        for chunk2 in self.fetch_in_chunks(summary_query):

            for row2 in chunk2:

                total_days=row2["total_days"] or 0

                present_days=row2["present_days"] or 0

                absent_days=row2["absent_days"] or 0

                attendance_percentage=0

                absent_percentage=0

                if total_days>0:

                    attendance_percentage=round(
                        (present_days/total_days)*100,
                        2
                    )

                    absent_percentage=round(
                        (absent_days/total_days)*100,
                        2
                    )

                attendance_summary[

                    (
                        row2["student_id"],
                        row2["academic_yr"]
                    )

                ]={

                    "total_days":total_days,
                    "present_days":present_days,
                    "absent_days":absent_days,
                    "attendance_percentage":attendance_percentage,
                    "absent_percentage":absent_percentage

                }

        existing_student_attendance={

            (
                sa.session.id,
                sa.student_enrollment.id
            ):sa

            for sa in StudentAttendance.objects.filter(
                school=school_obj
            ).select_related(
                "session",
                "student_enrollment"
            )
        }

        for chunk in self.fetch_in_chunks(query):

            attendance_to_create=[]

            for row in chunk:

                enrollment_obj=enrollment_map.get(

                    (
                        row["student_id"],
                        row["academic_yr"]
                    )
                )

                session_obj=session_map.get(

                    (
                        row["class_id"],
                        row["section_id"],
                        row["subject_id"],
                        row["only_date"]
                    )
                )

                if not enrollment_obj or not session_obj:
                    continue

                summary=attendance_summary.get(

                    (
                        row["student_id"],
                        row["academic_yr"]
                    ),
                    {}
                )

                key=(
                    session_obj.id,
                    enrollment_obj.id
                )

                if key in existing_student_attendance:
                    continue

                is_present=row["attendance_status"]=="0"

                attendance_to_create.append(

                    StudentAttendance(

                        school=school_obj,

                        source_student_attendance_id=
                        row["attendance_id"],

                        session=session_obj,

                        student_enrollment=enrollment_obj,

                        status="Present"
                        if is_present
                        else "Absent",

                        is_present=is_present,

                        present_days=summary.get(
                            "present_days",
                            0
                        ),

                        absent_days=summary.get(
                            "absent_days",
                            0
                        ),

                        total_school_days=summary.get(
                            "total_days",
                            0
                        ),

                        attendance_percentage=summary.get(
                            "attendance_percentage",
                            0
                        ),

                        absent_percentage=summary.get(
                            "absent_percentage",
                            0
                        )

                    )
                )

                existing_student_attendance[
                    key
                ] = True

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



    def sync_teacher_attendance(self,school_obj):
       

        query="""
            SELECT

            teacher_attendace_id,

            employee_id,
            punch_time,
            date

            FROM teacher_attendance
        """

        working_days_query="""
            SELECT

            COUNT(DISTINCT only_date) as total_days,

            academic_yr

            FROM attendance

            GROUP BY academic_yr
        """

        working_days_map={}

        for chunk2 in self.fetch_in_chunks(
            working_days_query
        ):

            for row2 in chunk2:

                working_days_map[
                    row2["academic_yr"]
                ]=row2["total_days"]

        teacher_map={

            str(t.employee_id):t

            for t in Teacher.objects.filter(
                school=school_obj
            )
        }

        teacher_yearly_summary={}

        summary_query="""
            SELECT

            ta.employee_id,

            a.academic_yr,

            COUNT(DISTINCT ta.date) as present_days

            FROM teacher_attendance ta

            LEFT JOIN attendance a
            ON a.only_date=ta.date

            GROUP BY
            ta.employee_id,
            a.academic_yr
        """

        for chunk3 in self.fetch_in_chunks(
            summary_query
        ):

            for row3 in chunk3:

                total_working_days=working_days_map.get(
                    row3["academic_yr"],
                    0
                )

                present_days=row3["present_days"] or 0

                absent_days=(
                    total_working_days-present_days
                )

                attendance_percentage=0

                absent_percentage=0

                if total_working_days>0:

                    attendance_percentage=round(
                        (
                            present_days/
                            total_working_days
                        )*100,
                        2
                    )

                    absent_percentage=round(
                        (
                            absent_days/
                            total_working_days
                        )*100,
                        2
                    )

                teacher_yearly_summary[

                    (
                        str(row3["employee_id"]),
                        row3["academic_yr"]
                    )

                ]={

                    "present_days":present_days,

                    "absent_days":absent_days,

                    "total_working_days":
                    total_working_days,

                    "attendance_percentage":
                    attendance_percentage,

                    "absent_percentage":
                    absent_percentage

                }

        existing_teacher_attendance={

            (
                ta.teacher.id,
                ta.date
            ):ta

            for ta in TeacherAttendance.objects.filter(
                school=school_obj
            ).select_related(
                "teacher"
            )
        }

        for chunk in self.fetch_in_chunks(query):

            attendance_to_create=[]

            for row in chunk:

                teacher_obj=teacher_map.get(
                    str(row["employee_id"])
                )

                if not teacher_obj:
                    continue

                academic_yr=None

                for key in teacher_yearly_summary.keys():

                    if key[0]==str(row["employee_id"]):

                        academic_yr=key[1]
                        break

                summary=teacher_yearly_summary.get(

                    (
                        str(row["employee_id"]),
                        academic_yr
                    ),
                    {}

                )

                key=(

                    teacher_obj.id,

                    row["date"]

                )

                if key in existing_teacher_attendance:
                    continue

                attendance_to_create.append(

                    TeacherAttendance(

                        school=school_obj,

                        source_teacher_attendance_id=
                        row["teacher_attendace_id"],

                        teacher=teacher_obj,

                        date=row["date"],

                        punch_time=row["punch_time"],

                        is_present=True,

                        present_days=summary.get(
                            "present_days",
                            0
                        ),

                        absent_days=summary.get(
                            "absent_days",
                            0
                        ),

                        total_working_days=summary.get(
                            "total_working_days",
                            0
                        ),

                        attendance_percentage=summary.get(
                            "attendance_percentage",
                            0
                        ),

                        absent_percentage=summary.get(
                            "absent_percentage",
                            0
                        )

                    )
                )

                existing_teacher_attendance[
                    key
                ]=True

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
    # MAIN HANDLER
    # ==========================================
    def handle(self, *args, **kwargs):

        import traceback

        try:

            self.stdout.write(
                self.style.WARNING(
                    "Starting school sync..."
                )
            )

            print("1. SCHOOL")
            school_obj = self.sync_school_data()

            if not school_obj:

                self.stdout.write(
                    self.style.ERROR(
                        "School sync failed"
                    )
                )

                return

            print("2. DEPARTMENTS")
            self.sync_departments(school_obj)

            print("3. CLASSES")
            self.sync_classes(school_obj)

            print("4. DIVISIONS")
            self.sync_divisions(school_obj)

            print("5. PARENTS")
            self.sync_parents(school_obj)

            print("6. USERS")
            self.sync_users(school_obj)

            print("7. TEACHERS")
            self.sync_teachers(school_obj)

            print("8. DEPARTMENT SPECIAL ROLES")
            self.sync_department_special_roles(
                school_obj
            )

            print("9. STUDENTS")
            self.sync_students(school_obj)

            print("10. STUDENT ENROLLMENTS")
            self.sync_student_enrollments(
                school_obj
            )

            print("11. SUBJECT MASTER")
            self.sync_subject_master(
                school_obj
            )

            print("12. SUBJECTS")
            self.sync_subjects(
                school_obj
            )

            print("13. SUBJECT REPORT CARD MASTER")
            self.sync_subject_report_card_master(
                school_obj
            )

            print("14. SUBJECT REPORT CARD")
            self.sync_subject_report_cards(
                school_obj
            )

            print("15. EXAM TYPES")
            self.sync_exam_types(
                school_obj
            )

            print("16. EXAMS")
            self.sync_exams(
                school_obj
            )

            print("17. EXAM SUBJECTS")
            self.sync_exam_subjects(
                school_obj
            )

            print("18. MARKS")
            self.sync_marks(
                school_obj
            )

            print("19. ATTENDANCE SESSIONS")
            self.sync_attendance_sessions(
                school_obj
            )

            print("20. STUDENT ATTENDANCE")
            self.sync_student_attendance(
                school_obj
            )

            print("21. TEACHER ATTENDANCE")
            self.sync_teacher_attendance(
                school_obj
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Sync completed successfully"
                )
            )

        except Exception:

            traceback.print_exc()

            raise



    

