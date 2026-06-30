from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone
import json

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

    BATCH_SIZE = 1000

    # ==========================================
    # COMMON LOGGER
    # ==========================================

    def log_sync(
        self,
        school,
        source_table,
        source_primary_id,
        target_table,
        target_primary_id,
        action,
        status,
        error_message=""
    ):

        if school:

            SyncTracker.objects.create(
                school=school,
                source_table=source_table,
                source_primary_id=str(source_primary_id),
                target_table=target_table,
                target_primary_id=target_primary_id,
                sync_action=action,
                sync_status=status,
                synced_at=timezone.now(),
                error_message=error_message
            )

    # ==========================================
    # FETCH MYSQL DATA IN CHUNKS
    # ==========================================

    def fetch_in_chunks(self, query):

        mysql_connection = connections["mysql"]

        with mysql_connection.cursor() as cursor:

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

    # ==========================================
    # SCHOOL + ACADEMIC YEARS
    # ==========================================

    def sync_school_data(self):

        self.stdout.write(
            self.style.WARNING(
                "Starting school + academic year sync..."
            )
        )

        query = """
            SELECT
                institute_name,
                short_name,
                address,
                academic_yr,
                academic_yr_from,
                academic_yr_to,
                active
            FROM settings
        """

        all_rows = []

        for chunk in self.fetch_in_chunks(query):

            self.stdout.write(
                f"Fetched {len(chunk)} settings rows"
            )

            all_rows.extend(chunk)

        school_obj = None

        # =================================
        # CREATE SCHOOL
        # =================================

        for row in all_rows:

            try:

                if row["short_name"]:

                    school_obj, created = School.objects.update_or_create(

                        short_name=row["short_name"],

                        defaults={
                            "name": row["institute_name"],
                            "address": row["address"] or "",
                            "city": "",
                            "state": "",
                            "country": ""
                        }
                    )

                    action = "INSERT" if created else "UPDATE"

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"School {action} : {row['short_name']}"
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="settings",
                        source_primary_id=row["short_name"],
                        target_table="schools",
                        target_primary_id=school_obj.id,
                        action=action,
                        status="SUCCESS"
                    )

                    break

            except Exception as e:

                self.stdout.write(
                    self.style.ERROR(
                        f"School sync failed : {str(e)}"
                    )
                )

                self.log_sync(
                    school=school_obj,
                    source_table="settings",
                    source_primary_id=row.get("short_name", ""),
                    target_table="schools",
                    target_primary_id=0,
                    action="INSERT",
                    status="FAILED",
                    error_message=str(e)
                )

        if not school_obj:
            return None

        # =================================
        # ACADEMIC YEARS
        # =================================

        for row in all_rows:

            try:

                if row["academic_yr"]:

                    academic_year_obj, created = AcademicYear.objects.update_or_create(
                        school=school_obj,
                        name=row["academic_yr"],
                        defaults={
                            "start_date": row["academic_yr_from"],
                            "end_date": row["academic_yr_to"],
                            "is_active": str(row["active"]).upper() == "Y"
                        }
                    )

                    action = "INSERT" if created else "UPDATE"

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Academic Year {action} : {row['academic_yr']}"
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="settings",
                        source_primary_id=row["academic_yr"],
                        target_table="academic_years",
                        target_primary_id=academic_year_obj.id,
                        action=action,
                        status="SUCCESS"
                    )

            except Exception as e:

                self.stdout.write(
                    self.style.ERROR(
                        f"Academic year sync failed : {str(e)}"
                    )
                )

                self.log_sync(
                    school=school_obj,
                    source_table="settings",
                    source_primary_id=row.get("academic_yr", ""),
                    target_table="academic_years",
                    target_primary_id=0,
                    action="INSERT",
                    status="FAILED",
                    error_message=str(e)
                )

        self.stdout.write(
            self.style.SUCCESS(
                "School + academic year sync completed"
            )
        )

        return school_obj

    # ==========================================
    # USERS
    # ==========================================

    def sync_users(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting users sync..."
            )
        )

        query = """
            SELECT
                user_id,
                name,
                password,
                reg_id,
                role_id,
                IsDelete
            FROM user_master
        """

        for chunk in self.fetch_in_chunks(query):

            self.stdout.write(
                f"Processing {len(chunk)} users..."
            )

            users_to_create = []
            users_to_update = []

            existing_users = {
                (user.role, user.reg_id): user
                for user in User.objects.filter(
                    school=school_obj
                )}

            for row in chunk:

                try:

                    existing_user = existing_users.get(
                        (row["role_id"], row["reg_id"])
                    )

                    # UPDATE

                    if existing_user:

                        existing_user.name = row["name"]
                        existing_user.password = row["password"]
                        existing_user.role = row["role_id"]

                        users_to_update.append(existing_user)

                        action = "UPDATE"

                    # INSERT

                    else:

                        user_obj = User(
                            school=school_obj,
                            reg_id=row["reg_id"],
                            name=row["name"],
                            email=row["user_id"],
                            password=row["password"],
                            role=row["role_id"]
                        )

                        users_to_create.append(user_obj)

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="user_master",
                        source_primary_id=row["user_id"],
                        target_table="users",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.stdout.write(
                        self.style.ERROR(
                            f"User sync failed : {str(e)}"
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="user_master",
                        source_primary_id=row.get("user_id", ""),
                        target_table="users",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            # BULK CREATE

            if users_to_create:

                User.objects.bulk_create(
                    users_to_create,
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(users_to_create)} users inserted"
                    )
                )

            # BULK UPDATE

            if users_to_update:

                User.objects.bulk_update(
                    users_to_update,
                    [
                        "name",
                        "password",
                        "role"
                    ],
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(users_to_update)} users updated"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Users sync completed"
            )
        )

    # ==========================================
    # PARENTS
    # ==========================================

    def sync_parents(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting parents sync..."
            )
        )

        query = """
            SELECT
                parent_id,
                father_name,
                mother_name,
                f_mobile,
                m_mobile,
                f_email,
                f_qualification
            FROM parent
        """

        for chunk in self.fetch_in_chunks(query):

            self.stdout.write(
                f"Processing {len(chunk)} parents..."
            )

            parents_to_create = []
            parents_to_update = []

            existing_parents = {
                parent.unique_user_id: parent
                for parent in Parent.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    existing_parent = existing_parents.get(
                        str(row["parent_id"])
                    )

                    if existing_parent:

                        existing_parent.father_name = (
                            row["father_name"] or ""
                        )

                        existing_parent.mother_name = (
                            row["mother_name"] or ""
                        )

                        existing_parent.father_phone = (
                            row["f_mobile"] or ""
                        )

                        existing_parent.mother_phone = (
                            row["m_mobile"] or ""
                        )

                        existing_parent.email = (
                            row["f_email"] or ""
                        )

                        existing_parent.education = (
                            row["f_qualification"] or ""
                        )

                        existing_parent.income = 0

                        parents_to_update.append(
                            existing_parent
                        )

                        action = "UPDATE"

                    else:

                        parent_obj = Parent(

                            school=school_obj,

                            unique_user_id=str(
                                row["parent_id"]
                            ),

                            father_name=(
                                row["father_name"] or ""
                            ),

                            mother_name=(
                                row["mother_name"] or ""
                            ),

                            father_phone=(
                                row["f_mobile"] or ""
                            ),

                            mother_phone=(
                                row["m_mobile"] or ""
                            ),

                            email=(
                                row["f_email"] or ""
                            ),

                            education=(
                                row["f_qualification"] or ""
                            ),

                            income=0
                        )

                        parents_to_create.append(
                            parent_obj
                        )

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="parent",
                        source_primary_id=row["parent_id"],
                        target_table="parents",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.stdout.write(
                        self.style.ERROR(
                            f"Parent sync failed : {str(e)}"
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="parent",
                        source_primary_id=row.get(
                            "parent_id", ""
                        ),
                        target_table="parents",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            if parents_to_create:

                Parent.objects.bulk_create(
                    parents_to_create,
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(parents_to_create)} parents inserted"
                    )
                )

            if parents_to_update:

                Parent.objects.bulk_update(
                    parents_to_update,
                    [
                        "father_name",
                        "mother_name",
                        "father_phone",
                        "mother_phone",
                        "email",
                        "education",
                        "income"
                    ],
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(parents_to_update)} parents updated"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Parents sync completed"
            )
        )


    # ==========================================
    # DEPARTMENTS
    # ==========================================

    def sync_departments(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting departments sync..."
            )
        )

        query = """
            SELECT
                department_id,
                name,
                academic_yr,
                created_at,
                updated_at
            FROM department
        """

        for chunk in self.fetch_in_chunks(query):

            departments_to_create = []
            departments_to_update = []

            existing_departments = {

                dept.source_department_id: dept

                for dept in Department.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    existing_department = existing_departments.get(
                        row["department_id"]
                    )

                    if existing_department:

                        existing_department.name = row["name"]
                        existing_department.academic_yr = row["academic_yr"]
                        existing_department.created_at = row["created_at"]
                        existing_department.updated_at = row["updated_at"]

                        departments_to_update.append(
                            existing_department
                        )

                        action = "UPDATE"

                    else:

                        department_obj = Department(

                            school=school_obj,

                            source_department_id=row[
                                "department_id"
                            ],

                            name=row["name"],

                            academic_yr=row[
                                "academic_yr"
                            ],

                            created_at=row[
                                "created_at"
                            ],

                            updated_at=row[
                                "updated_at"
                            ]
                        )

                        departments_to_create.append(
                            department_obj
                        )

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="department",
                        source_primary_id=row[
                            "department_id"
                        ],
                        target_table="department",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.log_sync(
                        school=school_obj,
                        source_table="department",
                        source_primary_id=row.get(
                            "department_id", ""
                        ),
                        target_table="department",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            if departments_to_create:

                Department.objects.bulk_create(
                    departments_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if departments_to_update:

                Department.objects.bulk_update(
                    departments_to_update,
                    [
                        "name",
                        "academic_yr",
                        "created_at",
                        "updated_at"
                    ],
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Departments sync completed"
            )
        )


    # ==========================================
    # CLASSES
    # ==========================================

    def sync_classes(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting classes sync..."
            )
        )

        query = """
            SELECT
                class_id,
                name,
                department_id,
                academic_yr,
                created_at,
                updated_at
            FROM class
        """

        department_map = {

            dept.source_department_id: dept

            for dept in Department.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            classes_to_create = []
            classes_to_update = []

            existing_classes = {

                cls.source_class_id: cls

                for cls in Class.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    department_obj = department_map.get(
                        row["department_id"]
                    )

                    existing_class = existing_classes.get(
                        row["class_id"]
                    )

                    if existing_class:

                        existing_class.name = row["name"]
                        existing_class.department = department_obj

                        classes_to_update.append(
                            existing_class
                        )

                        action = "UPDATE"

                    else:

                        class_obj = Class(

                            school=school_obj,

                            source_class_id=row[
                                "class_id"
                            ],

                            name=row["name"],

                            department=department_obj
                        )

                        classes_to_create.append(
                            class_obj
                        )

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="class",
                        source_primary_id=row[
                            "class_id"
                        ],
                        target_table="class",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.log_sync(
                        school=school_obj,
                        source_table="class",
                        source_primary_id=row.get(
                            "class_id", ""
                        ),
                        target_table="class",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            if classes_to_create:

                Class.objects.bulk_create(
                    classes_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if classes_to_update:

                Class.objects.bulk_update(
                    classes_to_update,
                    [
                        "name",
                        "department"
                    ],
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Classes sync completed"
            )
        )

    # ==========================================
    # DIVISIONS
    # ==========================================

    def sync_divisions(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting divisions sync..."
            )
        )

        query = """
            SELECT
                section_id,
                name,
                class_id,
                academic_yr
            FROM section
        """

        class_map = {

            cls.source_class_id: cls

            for cls in Class.objects.filter(
                school=school_obj
            )
        }

        academic_year_map = {

            yr.name: yr

            for yr in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            divisions_to_create = []
            divisions_to_update = []

            existing_divisions = {

                div.source_section_id: div

                for div in Division.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    class_obj = class_map.get(
                        row["class_id"]
                    )

                    academic_year_obj = academic_year_map.get(
                        row["academic_yr"]
                    )

                    if not class_obj or not academic_year_obj:
                        continue

                    existing_division = existing_divisions.get(
                        row["section_id"]
                    )

                    if existing_division:

                        existing_division.name = row["name"]

                        existing_division.class_ref = (
                            class_obj
                        )

                        existing_division.academic_year = (
                            academic_year_obj
                        )

                        existing_division.school = (
                            school_obj
                        )

                        divisions_to_update.append(
                            existing_division
                        )

                        action = "UPDATE"

                    else:

                        division_obj = Division(

                            school=school_obj,

                            source_section_id=row[
                                "section_id"
                            ],

                            class_ref=class_obj,

                            academic_year=academic_year_obj,

                            name=row["name"]
                        )

                        divisions_to_create.append(
                            division_obj
                        )

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="section",
                        source_primary_id=row[
                            "section_id"
                        ],
                        target_table="division",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.log_sync(
                        school=school_obj,
                        source_table="section",
                        source_primary_id=row.get(
                            "section_id", ""
                        ),
                        target_table="division",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            if divisions_to_create:

                Division.objects.bulk_create(
                    divisions_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if divisions_to_update:

                Division.objects.bulk_update(
                    divisions_to_update,
                    [
                        "name",
                        "class_ref",
                        "academic_year",
                        "school"
                    ],
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Divisions sync completed"
            )
        )

    # ==========================================
    # DEPARTMENT SPECIAL ROLES
    # ==========================================

    def sync_department_special_roles(
        self,
        school_obj
    ):

        self.stdout.write(
            self.style.WARNING(
                "Starting department special roles sync..."
            )
        )

        query = """
            SELECT
                special_role_id,
                department_id,
                teacher_id,
                role,
                academic_yr
            FROM department_special_role
        """
#removed the school id 
        department_map = {

            dept.source_department_id: dept

            for dept in Department.objects.filter(
                school=school_obj
            )
        }

        user_map = {

            user.reg_id: user

            for user in User.objects.filter(
                school=school_obj
            )

            if user.reg_id
        }

        school_instance = school_obj
      

        for chunk in self.fetch_in_chunks(query):

            for row in chunk:

                try:

                    department_obj = department_map.get(
                        row["department_id"]
                    )

                    teacher_obj = user_map.get(
                        row["teacher_id"]
                    )
                    school_instance = school_obj
                    if (

                        not department_obj
                        or not teacher_obj
                    ):
                        continue

                    obj, created = (
                        DepartmentSpecialRole.objects
                        .update_or_create(

                            school=school_instance,
                            department=department_obj,
                            teacher=teacher_obj,
                            role=row["role"],

                            defaults={
                                "academic_yr": row[
                                    "academic_yr"
                                ]
                            }
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="department_special_role",
                        source_primary_id=row[
                            "special_role_id"
                        ],
                        target_table="department_special_role",
                        target_primary_id=obj.id,
                        action=(
                            "INSERT"
                            if created
                            else "UPDATE"
                        ),
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.log_sync(
                        school=school_obj,
                        source_table="department_special_role",
                        source_primary_id=row.get(
                            "special_role_id",
                            ""
                        ),
                        target_table="department_special_role",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Department special roles sync completed"
            )
        )

    # ========================================== #
    # STUDENTS #
    # ========================================== #

    def sync_students(self, school_obj):

        self.stdout.write(
            self.style.WARNING("Starting students sync...")
        )

        query = """
            SELECT
                student_id,
                parent_id,
                first_name,
                mid_name,
                last_name,
                dob,
                gender
            FROM student
        """

        parent_map = {
            str(parent.unique_user_id): parent
            for parent in Parent.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            self.stdout.write(
                f"Processing {len(chunk)} students..."
            )

            students_to_create = []
            students_to_update = []

            existing_students = {
                student.unique_user_id: student
                for student in Student.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    parent_obj = parent_map.get(
                        str(row["parent_id"])
                    )

                    if not parent_obj:
                        continue

                    student_id = str(
                        row["student_id"]
                    )

                    existing_student = existing_students.get(
                        student_id
                    )

                    if existing_student:

                        existing_student.parent = parent_obj
                        existing_student.first_name = (
                            row["first_name"] or ""
                        )
                        existing_student.middle_name = (
                            row["mid_name"] or ""
                        )
                        existing_student.last_name = (
                            row["last_name"] or ""
                        )
                        existing_student.dob = row["dob"]
                        existing_student.gender = (
                            row["gender"] or ""
                        )

                        students_to_update.append(
                            existing_student
                        )

                        action = "UPDATE"

                    else:

                        student_obj = Student(
                            school=school_obj,
                            parent=parent_obj,
                            unique_user_id=student_id,
                            first_name=row["first_name"] or "",
                            middle_name=row["mid_name"] or "",
                            last_name=row["last_name"] or "",
                            dob=row["dob"],
                            gender=row["gender"] or ""
                        )

                        students_to_create.append(
                            student_obj
                        )

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="student",
                        source_primary_id=row["student_id"],
                        target_table="students",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.stdout.write(
                        self.style.ERROR(
                            f"Student sync failed : {str(e)}"
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="student",
                        source_primary_id=row.get(
                            "student_id", ""
                        ),
                        target_table="students",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            if students_to_create:

                Student.objects.bulk_create(
                    students_to_create,
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(students_to_create)} students inserted"
                    )
                )

            if students_to_update:

                Student.objects.bulk_update(
                    students_to_update,
                    [
                        "parent",
                        "first_name",
                        "middle_name",
                        "last_name",
                        "dob",
                        "gender"
                    ],
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(students_to_update)} students updated"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Students sync completed"
            )
        )

    # ========================================== #
    # STUDENT ENROLLMENTS #
    # ========================================== #
    def sync_student_enrollments(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting student enrollments sync..."
            )
        )

        query = """
            SELECT
                student_id,
                academic_yr,
                section_id,
                roll_no,
                isActive
            FROM student
        """

        student_map = {

            student.unique_user_id: student

            for student in Student.objects.filter(
                school=school_obj
            )
        }

        division_map = {

            division.source_section_id: division

            for division in Division.objects.filter(
                school=school_obj
            )
        }

        academic_year_map = {

            year.name: year

            for year in AcademicYear.objects.filter(
                school=school_obj
            )
        }

        for chunk in self.fetch_in_chunks(query):

            self.stdout.write(
                f"Processing {len(chunk)} enrollments..."
            )

            enrollments_to_create = []
            enrollments_to_update = []

            existing_enrollments = {

                (
                    enrollment.student.id,
                    enrollment.academic_year.id
                ): enrollment

                for enrollment in StudentEnrollment.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    student_obj = student_map.get(
                        str(row["student_id"])
                    )

                    if not student_obj:
                        continue

                    division_obj = division_map.get(
                        row["section_id"]
                    )

                    if not division_obj:
                        continue

                    academic_year_obj = academic_year_map.get(
                        row["academic_yr"]
                    )

                    if not academic_year_obj:
                        continue

                    enrollment_key = (
                        student_obj.id,
                        academic_year_obj.id
                    )

                    existing_enrollment = (
                        existing_enrollments.get(
                            enrollment_key
                        )
                    )

                    status = (
                        "ACTIVE"
                        if row["isActive"] == "Y"
                        else "INACTIVE"
                    )

                    if existing_enrollment:

                        existing_enrollment.division = (
                            division_obj
                        )

                        existing_enrollment.roll_number = (
                            str(row["roll_no"] or "")
                        )

                        existing_enrollment.status = (
                            status
                        )

                        existing_enrollment.school = (
                            school_obj
                        )

                        enrollments_to_update.append(
                            existing_enrollment
                        )

                        action = "UPDATE"

                    else:

                        enrollment_obj = (
                            StudentEnrollment(

                                school=school_obj,

                                student=student_obj,

                                division=division_obj,

                                academic_year=academic_year_obj,

                                roll_number=str(
                                    row["roll_no"] or ""
                                ),

                                status=status
                            )
                        )

                        enrollments_to_create.append(
                            enrollment_obj
                        )

                        action = "INSERT"

                    self.log_sync(
                        school=school_obj,
                        source_table="student",
                        source_primary_id=row["student_id"],
                        target_table="student_enrollment",
                        target_primary_id=0,
                        action=action,
                        status="SUCCESS"
                    )

                except Exception as e:

                    self.stdout.write(
                        self.style.ERROR(
                            f"Enrollment sync failed : {str(e)}"
                        )
                    )

                    self.log_sync(
                        school=school_obj,
                        source_table="student",
                        source_primary_id=row.get(
                            "student_id", ""
                        ),
                        target_table="student_enrollment",
                        target_primary_id=0,
                        action="INSERT",
                        status="FAILED",
                        error_message=str(e)
                    )

            if enrollments_to_create:

                StudentEnrollment.objects.bulk_create(
                    enrollments_to_create,
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(enrollments_to_create)} enrollments inserted"
                    )
                )

            if enrollments_to_update:

                StudentEnrollment.objects.bulk_update(
                    enrollments_to_update,
                    [
                        "division",
                        "roll_number",
                        "status",
                        "school"
                    ],
                    batch_size=self.BATCH_SIZE
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(enrollments_to_update)} enrollments updated"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Student enrollments sync completed"
            )
        )

    def sync_teachers(self,school_obj):

        query="""
            SELECT teacher_id,employee_id,name,birthday,
            date_of_joining,sex,email,designation,
            academic_qual,professional_qual,special_sub,
            trained,experience,class_id,section_id,isDelete
            FROM teacher
        """

        class_map={c.source_class_id:c for c in Class.objects.filter(school=school_obj)}

        division_map={d.source_section_id:d for d in Division.objects.filter(school=school_obj)}

        existing_teachers={t.teacher_id:t for t in Teacher.objects.filter(school=school_obj)}

        for chunk in self.fetch_in_chunks(query):

            teachers_to_create=[]
            teachers_to_update=[]

            for row in chunk:

                try:

                    class_obj=class_map.get(row["class_id"])

                    division_obj=division_map.get(row["section_id"])

                    existing_teacher=existing_teachers.get(row["teacher_id"])

                    if existing_teacher:

                        existing_teacher.employee_id=row["employee_id"]
                        existing_teacher.name=row["name"]
                        existing_teacher.birthday=row["birthday"]
                        existing_teacher.date_of_joining=row["date_of_joining"]
                        existing_teacher.sex=row["sex"]
                        existing_teacher.email=row["email"]
                        existing_teacher.designation=row["designation"]
                        existing_teacher.academic_qual=row["academic_qual"]
                        existing_teacher.professional_qual=row["professional_qual"]
                        existing_teacher.special_sub=row["special_sub"]
                        existing_teacher.trained=row["trained"]
                        existing_teacher.experience=row["experience"]
                        existing_teacher.class_ref=class_obj
                        existing_teacher.division=division_obj
                        existing_teacher.is_delete=row["isDelete"]

                        teachers_to_update.append(existing_teacher)

                    else:

                        teachers_to_create.append(

                            Teacher(

                                school=school_obj,
                                teacher_id=row["teacher_id"],
                                employee_id=row["employee_id"],
                                name=row["name"],
                                birthday=row["birthday"],
                                date_of_joining=row["date_of_joining"],
                                sex=row["sex"],
                                email=row["email"],
                                designation=row["designation"],
                                academic_qual=row["academic_qual"],
                                professional_qual=row["professional_qual"],
                                special_sub=row["special_sub"],
                                trained=row["trained"],
                                experience=row["experience"],
                                class_ref=class_obj,
                                division=division_obj,
                                is_delete=row["isDelete"]

                            )
                        )

                except Exception as e:

                    print(f"Teacher sync failed:{str(e)}")

            if teachers_to_create:

                Teacher.objects.bulk_create(
                    teachers_to_create,
                    batch_size=self.BATCH_SIZE
                )

            if teachers_to_update:

                Teacher.objects.bulk_update(
                    teachers_to_update,
                    [
                        "employee_id","name","birthday",
                        "date_of_joining","sex","email",
                        "designation","academic_qual",
                        "professional_qual","special_sub",
                        "trained","experience","class_ref",
                        "division","is_delete"
                    ],
                    batch_size=self.BATCH_SIZE
                )

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

