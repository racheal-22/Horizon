from django.core.management.base import BaseCommand
from django.db import connections

from app.models import School, AcademicYear, User, SyncTracker


class Command(BaseCommand):

    # =========================
    # SCHOOL + ACADEMIC YEAR
    # =========================

    def sync_school_data(self):

        mysql_connection = connections["mysql"]

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

        with mysql_connection.cursor() as cursor:

            cursor.execute(query)

            columns = [col[0] for col in cursor.description]

            rows = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        school_obj = None

        # Create school from only row having short_name
        for row in rows:

            if row["short_name"]:

                school_obj, created = School.objects.get_or_create(
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

                SyncTracker.objects.create(
                    school=school_obj,
                    source_table="settings",
                    source_primary_id=row["short_name"],
                    target_table="school",
                    target_primary_id=school_obj.id,
                    sync_action=action,
                    sync_status="SUCCESS"
                )

                break

        # Create all academic years using same school
        for row in rows:

            try:

                if school_obj and row["academic_yr"]:

                    academic_year_obj, created = AcademicYear.objects.get_or_create(
                        school=school_obj,
                        name=row["academic_yr"],
                        defaults={
                            "start_date": row["academic_yr_from"],
                            "end_date": row["academic_yr_to"],
                            "is_active": bool(row["active"])
                        }
                    )

                    action = "INSERT" if created else "UPDATE"

                    SyncTracker.objects.create(
                        school=school_obj,
                        source_table="settings",
                        source_primary_id=row["academic_yr"],
                        target_table="academic_year",
                        target_primary_id=academic_year_obj.id,
                        sync_action=action,
                        sync_status="SUCCESS"
                    )

            except Exception as e:

                SyncTracker.objects.create(
                    school=school_obj,
                    source_table="settings",
                    source_primary_id=row.get("academic_yr"),
                    target_table="academic_year",
                    target_primary_id=0,
                    sync_action="INSERT",
                    sync_status="FAILED",
                    error_message=str(e)
                )


    # =========================
    # USERS
    # =========================

    def sync_users(self):

        mysql_connection = connections["mysql"]

        query = """
            SELECT
                user_id,
                name,
                password,
                reg_id,
                role_id
            FROM user_master
            WHERE IsDelete != 'Y'
        """

        with mysql_connection.cursor() as cursor:

            cursor.execute(query)

            columns = [col[0] for col in cursor.description]

            rows = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        school_obj = School.objects.first()

        for row in rows:

            try:

                user_obj = User.objects.filter(
                    school=school_obj,
                    unique_user_id=row["user_id"]
                ).first()

                if user_obj:

                    user_obj.name = row["name"]
                    user_obj.password = row["password"]
                    user_obj.role = row["role_id"]

                    user_obj.save()

                    action = "UPDATE"

                else:

                    user_obj = User.objects.create(
                        school=school_obj,
                        unique_user_id=row["user_id"],
                        name=row["name"],
                        email="",
                        password=row["password"],
                        role=row["role_id"]
                    )

                    action = "INSERT"

                SyncTracker.objects.create(
                    school=school_obj,
                    source_table="user_master",
                    source_primary_id=row["user_id"],
                    target_table="user",
                    target_primary_id=user_obj.id,
                    sync_action=action,
                    sync_status="SUCCESS"
                )

            except Exception as e:

                SyncTracker.objects.create(
                    school=school_obj,
                    source_table="user_master",
                    source_primary_id=row.get("user_id"),
                    target_table="user",
                    target_primary_id=0,
                    sync_action="INSERT",
                    sync_status="FAILED",
                    error_message=str(e)
                )
    # =========================
    # MAIN HANDLER
    # =========================

    def handle(self, *args, **kwargs):

        sync_methods = [
            self.sync_school_data,
            self.sync_users,
        ]

        for method in sync_methods:

            try:

                method()

                self.stdout.write(
                    self.style.SUCCESS(f"{method.__name__} completed")
                )

            except Exception as e:

                self.stdout.write(
                    self.style.ERROR(f"{method.__name__} failed : {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS("Full sync completed successfully")
        )