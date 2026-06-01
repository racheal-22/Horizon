from django.core.management.base import BaseCommand
from django.db import connections

from app.models import (
    School,
    Student,
    Teacher,
    Book,
    BookIssue
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

    # ==========================================
    # BOOKS
    # ==========================================

    def sync_books(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting books sync..."
            )
        )

        query = """
            SELECT
                book_id,
                book_title,
                issue_type,
                author
            FROM book
        """

        existing_books = {
            b.source_book_id: b
            for b in Book.objects.filter(
                school=school_obj
            )
        }

        books_to_create = []

        for chunk in self.fetch_in_chunks(query):

            for row in chunk:

                if row["book_id"] in existing_books:
                    continue

                books_to_create.append(

                    Book(

                        school=school_obj,

                        source_book_id=row["book_id"],

                        title=row["book_title"],

                        type=row["issue_type"],

                        author=row["author"]
                    )
                )

            if books_to_create:

                Book.objects.bulk_create(
                    books_to_create,
                    batch_size=self.BATCH_SIZE
                )

                books_to_create = []

        self.stdout.write(
            self.style.SUCCESS(
                "Books sync completed"
            )
        )

    # ==========================================
    # BOOK ISSUES
    # ==========================================

    def sync_book_issues(self, school_obj):

        self.stdout.write(
            self.style.WARNING(
                "Starting book issues sync..."
            )
        )

        query = """
            SELECT
                member_id,
                member_type,
                book_id,
                issue_date,
                due_date,
                return_date
            FROM issue_return
        """

        # student.id matches member_id
        student_map = {

            s.id: s

            for s in Student.objects.filter(
                school=school_obj
            )
        }

        # teacher.teacher_id matches member_id
        teacher_map = {

            t.teacher_id: t

            for t in Teacher.objects.filter(
                school=school_obj
            )
        }

        # mysql book_id matches source_book_id
        book_map = {

            b.source_book_id: b

            for b in Book.objects.filter(
                school=school_obj
            )
        }

        existing_issues = {

            (
                bi.book_id,
                bi.student_id,
                bi.teacher_id,
                bi.issue_date
            ): bi

            for bi in BookIssue.objects.all()
        }

        for chunk in self.fetch_in_chunks(query):

            issues_to_create = []

            for row in chunk:

                student_obj = None
                teacher_obj = None

                # student issue
                if row["member_type"] == "S":

                    student_obj = student_map.get(
                        row["member_id"]
                    )

                # teacher issue
                elif row["member_type"] == "T":

                    teacher_obj = teacher_map.get(
                        row["member_id"]
                    )

                book_obj = book_map.get(
                    row["book_id"]
                )

                if not book_obj:
                    continue

                key = (
                    book_obj.id,
                    student_obj.id if student_obj else None,
                    teacher_obj.id if teacher_obj else None,
                    row["issue_date"]
                )

                if key in existing_issues:
                    continue

                return_date = row["return_date"]

                status = "Issued"

                if str(return_date) != "0000-00-00":

                    status = "Returned"

                issues_to_create.append(

                    BookIssue(

                        book=book_obj,

                        student=student_obj,

                        teacher=teacher_obj,

                        issue_date=row["issue_date"],

                        due_date=row["due_date"],

                        return_date=None if str(return_date) == "0000-00-00" else return_date,

                        member_type=row["member_type"],

                        status=status
                    )
                )

            if issues_to_create:

                BookIssue.objects.bulk_create(
                    issues_to_create,
                    batch_size=self.BATCH_SIZE
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Book issues sync completed"
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

        self.sync_books(
            school_obj
        )

        self.sync_book_issues(
            school_obj
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Library sync completed successfully"
            )
        )