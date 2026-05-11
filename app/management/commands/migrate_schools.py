from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

from app.models import (
    School,
    AcademicYear,
    User,
    SyncTracker,
    Parent
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
                            "is_active": bool(row["active"])
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
                user.unique_user_id: user
                for user in User.objects.filter(
                    school=school_obj
                )
            }

            for row in chunk:

                try:

                    existing_user = existing_users.get(
                        row["user_id"]
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
                            unique_user_id=row["user_id"],
                            name=row["name"],
                            email="",
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
                f_mobile,
                f_email,
                f_qualification,
                father_occupation,
                IsDelete
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

                    # UPDATE

                    if existing_parent:

                        existing_parent.name = (
                            row["father_name"] or ""
                        )

                        existing_parent.phone = (
                            row["f_mobile"] or ""
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

                    # INSERT

                    else:

                        parent_obj = Parent(

                            school=school_obj,

                            unique_user_id=str(
                                row["parent_id"]
                            ),

                            name=row["father_name"] or "",

                            education=row[
                                "f_qualification"
                            ] or "",

                            income=0,

                            phone=row["f_mobile"] or "",

                            email=row["f_email"] or ""
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

            # BULK CREATE

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

            # BULK UPDATE

            if parents_to_update:

                Parent.objects.bulk_update(
                    parents_to_update,
                    [
                        "name",
                        "education",
                        "income",
                        "phone",
                        "email"
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
    # MAIN HANDLER
    # ==========================================

    def handle(self, *args, **kwargs):

        try:

            self.stdout.write(
                self.style.WARNING(
                    "Starting school sync..."
                )
            )

            # SCHOOL + ACADEMIC YEARS

            school_obj = self.sync_school_data()

            if not school_obj:

                self.stdout.write(
                    self.style.ERROR(
                        "School sync failed"
                    )
                )

                return

            # PARENTS

            self.sync_parents(
                school_obj
            )

            # USERS

            self.sync_users(
                school_obj
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Sync completed successfully"
                )
            )

        except Exception as e:

            self.stdout.write(
                self.style.ERROR(
                    f"Sync failed : {str(e)}"
                )
            )