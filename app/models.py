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

    class Meta:
        db_table = "school"  

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
    
    class Meta:
        db_table = "sync_tracker"
# =========================
# USERS
# =========================
class User(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    name = models.CharField(max_length=255)
    email = models.EmailField()
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    reg_id = models.IntegerField(null=True, blank=True)
    class Meta:

        db_table = "users"

        unique_together = (
            "school",
            "role",
            "reg_id"
        )

    def __str__(self):

        return f"{self.name} ({self.role})"


# =========================
# ACADEMIC YEAR
# =========================
class AcademicYear(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "academic_year"



# =========================
# DEPARTMENT
# =========================


class Department(models.Model):

    school = models.ForeignKey(
        "School",
        on_delete=models.CASCADE,
        related_name="departments"
    )

    name = models.CharField(
        max_length=30
    )

    academic_yr = models.CharField(
        max_length=11
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    source_department_id = models.IntegerField(
        null=True,
        blank=True
)

    class Meta:
        db_table = "department"

    def __str__(self):
        return self.name
    



# =========================
# CLASS + DIVISION
# =========================
class Class(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        db_column="department_id",
        related_name="classes",
        null = True,
        blank = True
    )
    source_class_id = models.IntegerField(
        null=True,
        blank=True
)
    class Meta:
        db_table = "class"


class Division(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    class_teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    source_section_id = models.IntegerField(
        null=True,
        blank=True
    )
    class Meta:
        db_table = "division"
# =========================
# DEPARTMENT SPECIAL ROLE
# =========================

class DepartmentSpecialRole(models.Model):

    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        db_column="department_id",
        related_name="special_roles"
    )

    teacher = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        db_column="teacher_id",
        related_name="department_special_roles"
    )

    source_special_role_id = models.IntegerField(
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=17
    )

    academic_yr = models.CharField(
        max_length=11
    )

    class Meta:
        db_table = "department_special_role"

    def __str__(self):
        return f"{self.role} - {self.department.name}"


# =========================
# PARENTS + STUDENTS
# =========================
class Parent(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)

    father_name = models.CharField(max_length=255, blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)

    father_phone = models.CharField(max_length=20, blank=True, null=True)
    mother_phone = models.CharField(max_length=20, blank=True, null=True)

    unique_user_id = models.CharField(max_length=100, null=True, blank=True)

    education = models.CharField(max_length=255, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    email = models.EmailField(blank=True, null=True)

    class Meta:
        db_table = "parent"




class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    unique_user_id = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student"


# =========================
# STUDENT ENROLLMENT
# =========================
class StudentEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    roll_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = "student_enrollment"


# =========================
# TEACHER
# =========================

class Teacher(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    teacher_id = models.IntegerField(null=True, blank=True) #unique id taken from the source db 
    employee_id = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=255)
    birthday = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=10, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    academic_qual = models.CharField(max_length=255, null=True, blank=True)
    professional_qual = models.CharField(max_length=100, null=True, blank=True)
    special_sub = models.CharField(max_length=100, null=True, blank=True)
    trained = models.CharField(max_length=20, null=True, blank=True)
    experience = models.IntegerField(null=True, blank=True)

    class_ref = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    division = models.ForeignKey(
        Division,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    is_delete = models.CharField(max_length=1, default="N")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "teacher"

    def __str__(self):
        return self.name
    

# =========================
# SUBJECT MASTER
# =========================

class SubjectMaster(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    subject_type = models.CharField(max_length=20)
    source_sm_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "subject_master"

    def __str__(self):
        return self.name


# =========================
# SUBJECT
# =========================

class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    subject_master = models.ForeignKey(SubjectMaster, on_delete=models.CASCADE)

    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    source_subject_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subject"

    def __str__(self):
        return self.subject_master.name


# =========================
# SUBJECT REPORT CARD MASTER
# =========================

class SubjectReportCardMaster(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    sequence = models.IntegerField(null=True, blank=True)

    source_sub_rc_master_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subjects_on_report_card_master"

    def __str__(self):
        return self.name


# =========================
# SUBJECT REPORT CARD
# =========================

class SubjectReportCard(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    report_card_master = models.ForeignKey(
        SubjectReportCardMaster,
        on_delete=models.CASCADE
    )

    class_ref = models.ForeignKey(
        Class,
        on_delete=models.CASCADE
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE
    )

    subject_type = models.CharField(max_length=20)

    source_sub_reportcard_id = models.IntegerField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subjects_on_report_card"

    def __str__(self):
        return self.report_card_master.name



# =========================
# EXAMS
# =========================
class ExamType(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    weightage = models.DecimalField(max_digits=5, decimal_places=2)
    source_exam_type_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        db_table = "exam_type"


class Exam(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    exam_type = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    source_exam_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )
    name = models.CharField(max_length=255)
    start_date = models.DateField()

    class Meta:
        db_table = "exam"

class ExamSubject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    max_marks = models.IntegerField()
    source_exam_subject_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        db_table = "exam_subject"


class Mark(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    exam_subject = models.ForeignKey(ExamSubject, on_delete=models.CASCADE)
    obtained_marks = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    source_mark_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )

    percentage=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_present=models.CharField(
        max_length=1,
        default="Y"
    )

    exam_type=models.ForeignKey(
        ExamType,
        on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        db_table = "mark"

# =========================
# ATTENDANCE
# =========================
class AttendanceSession(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    class_ref=models.ForeignKey(
        Class,
        on_delete=models.CASCADE, null=True, blank=True
    )

    division=models.ForeignKey(
        Division,
        on_delete=models.CASCADE, null=True, blank=True
    )

    subject=models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    teacher=models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    academic_year=models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE, null=True, blank=True 
    )

    date=models.DateField()

    total_students=models.IntegerField(default=0)

    total_present=models.IntegerField(default=0)

    total_absent=models.IntegerField(default=0)

    attendance_percentage=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    source_attendance_session_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        db_table="attendance_session"

#student attendance for each session
class StudentAttendance(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    session=models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE
    )

    student_enrollment=models.ForeignKey(
        StudentEnrollment,
        on_delete=models.CASCADE
    )

    status=models.CharField(max_length=20)

    is_present=models.BooleanField(default=True)

    present_days=models.IntegerField(default=0)

    absent_days=models.IntegerField(default=0)

    total_school_days=models.IntegerField(default=0)

    attendance_percentage=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    absent_percentage=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    remarks=models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
 
    class Meta:
        db_table="student_attendance"


class TeacherAttendance(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    date=models.DateField()

    punch_time=models.DateTimeField(
        null=True,
        blank=True
    )

    is_present=models.BooleanField(
        default=True
    )

    present_days=models.IntegerField(
        default=0
    )

    absent_days=models.IntegerField(
        default=0
    )

    total_working_days=models.IntegerField(
        default=0
    )

    attendance_percentage=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    absent_percentage=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        db_table="teacher_attendance"
# =========================
# HOMEWORK
# =========================
class Homework(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateField()
    status = models.TextField()

    class Meta:
        db_table = "homework"

class HomeworkSubmission(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)

    class Meta:
        db_table = "homework_submission"


# =========================
# ACHIEVEMENTS
# =========================
class StudentAchievement(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    description = models.TextField()
    date = models.DateField()

    class Meta:
        db_table = "student_achievement"


class TeacherAchievement(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()

    class Meta:
        db_table = "teacher_achievement"


# =========================
# LIBRARY
# =========================
class Book(models.Model):

    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    source_book_id=models.IntegerField(
        null=True,
        blank=True
    )

    title=models.CharField(max_length=255)

    type=models.CharField(max_length=100)

    author=models.CharField(max_length=255)

    class Meta:
        db_table="book"


class BookIssue(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    book=models.ForeignKey(
        Book,
        on_delete=models.CASCADE
    )

    student=models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    teacher=models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    issue_date=models.DateField()

    due_date=models.DateField(
        null=True,
        blank=True
    )

    return_date=models.DateField(
        null=True,
        blank=True
    )

    member_type=models.CharField(
        max_length=1,null=True, blank=True
    )

    status=models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    class Meta:
        db_table="book_issue"


# =========================
# REMEDIAL
# =========================
class RemedialSession(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    session_date = models.DateField()
    notes = models.TextField()

    class Meta:
        db_table = "remedial_session"



# =========================
# HEALTH
# =========================
class StudentHealthRecord(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    height = models.DecimalField(max_digits=5, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    recorded_date = models.DateField()

    class Meta:
        db_table = "student_health_record"


# =========================
# PROJECTS
# =========================
class Project(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    type = models.CharField(max_length=100)

    class Meta:
        db_table = "project"

# =========================
# ANALYTICS
# =========================
class StudentYearSummary(models.Model):
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    avg_marks = models.DecimalField(max_digits=5, decimal_places=2)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    rank = models.IntegerField()
    achievement_id = models.IntegerField()

    class Meta:
        db_table = "student_year_summary"


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
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    class Meta:
        db_table = "teacher_activeness"


# =========================
# BEHAVIOR ANALYSIS
# =========================
class StudentBehaviorAnalysis(models.Model):
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)
    complaints_count = models.IntegerField()
    remarks = models.TextField()

    event_participation_score = models.DecimalField(max_digits=5, decimal_places=2)
    books_returned_on_time = models.IntegerField()
    homework_on_time = models.IntegerField()
    assignments_on_time = models.IntegerField()
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    overall_behavior_score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_behavior_analysis"


# =========================
# PARENT FEEDBACK
# =========================
class ParentFeedback(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    school = models.ForeignKey('School', on_delete=models.CASCADE, null=True, blank=True)

    feedback_text = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "parent_feedback"