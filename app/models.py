from django.db import models


# =========================
# SCHOOL
# =========================
class School(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, default="")
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

# =========================
# SYNC TRACKER
# =========================

class SyncTracker(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE)
    source_table = models.CharField(max_length=100)
    source_primary_id = models.CharField(max_length=100)
    target_table = models.CharField(max_length=100)
    target_primary_id = models.IntegerField()
    sync_action = models.CharField(max_length=20)  
    sync_status = models.CharField(max_length=20) 
    synced_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(null=True,blank=True)
# =========================
# USERS
# =========================
class User(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    unique_user_id = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('school', 'unique_user_id')


# =========================
# ACADEMIC YEAR
# =========================
class AcademicYear(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)


# =========================
# CLASS + DIVISION
# =========================
class Class(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)


class Division(models.Model):
    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    name = models.CharField(max_length=10)
    class_teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


# =========================
# PARENTS + STUDENTS
# =========================
class Parent(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    unique_user_id = models.CharField(max_length=100, null=True, blank=True)
    education = models.CharField(max_length=255)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=20)
    email = models.EmailField()


class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    unique_user_id = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField()
    gender = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# STUDENT ENROLLMENT
# =========================
class StudentEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20)


# =========================
# SUBJECTS + TEACHERS
# =========================
class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)


# =========================
# EXAMS
# =========================
class ExamType(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    weightage = models.DecimalField(max_digits=5, decimal_places=2)


class Exam(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    exam_type = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    start_date = models.DateField()


class ExamSubject(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    max_marks = models.IntegerField()


class Mark(models.Model):
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    exam_subject = models.ForeignKey(ExamSubject, on_delete=models.CASCADE)
    obtained_marks = models.DecimalField(max_digits=5, decimal_places=2)


# =========================
# ATTENDANCE
# =========================
class AttendanceSession(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    date = models.DateField()


class StudentAttendance(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)


class TeacherAttendance(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20)


# =========================
# HOMEWORK
# =========================
class Homework(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateField()
    status = models.TextField()


class HomeworkSubmission(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)


# =========================
# ACHIEVEMENTS
# =========================
class StudentAchievement(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    description = models.TextField()
    date = models.DateField()


class TeacherAchievement(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()


# =========================
# LIBRARY
# =========================
class Book(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    author = models.CharField(max_length=255)


class BookIssue(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    issue_date = models.DateField()
    return_date = models.DateField()


# =========================
# REMEDIAL
# =========================
class RemedialSession(models.Model):
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    session_date = models.DateField()
    notes = models.TextField()


# =========================
# HEALTH
# =========================
class StudentHealthRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    height = models.DecimalField(max_digits=5, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    recorded_date = models.DateField()


# =========================
# PROJECTS
# =========================
class Project(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    type = models.CharField(max_length=100)


# =========================
# TEACHER PROFILE
# =========================
class TeacherProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    qualification = models.CharField(max_length=255)
    experience_years = models.IntegerField()


# =========================
# ANALYTICS
# =========================
class StudentYearSummary(models.Model):
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    avg_marks = models.DecimalField(max_digits=5, decimal_places=2)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    rank = models.IntegerField()
    achievement_id = models.IntegerField()


# =========================
# TEACHER ACTIVENESS
# =========================
class TeacherActiveness(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    event_name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    assigned_date = models.DateField()
    status = models.CharField(max_length=50)


# =========================
# BEHAVIOR ANALYSIS
# =========================
class StudentBehaviorAnalysis(models.Model):
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

    complaints_count = models.IntegerField()
    remarks = models.TextField()

    event_participation_score = models.DecimalField(max_digits=5, decimal_places=2)
    books_returned_on_time = models.IntegerField()
    homework_on_time = models.IntegerField()
    assignments_on_time = models.IntegerField()
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    overall_behavior_score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# PARENT FEEDBACK
# =========================
class ParentFeedback(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

    feedback_text = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)