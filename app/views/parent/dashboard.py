
from django.shortcuts import render, redirect
from collections import OrderedDict
from collections import Counter
import json
from .analytics import (
    get_subject_performance_analytics,
    get_subject_growth_analytics,
   
)
from app.models import (
    User,   
    Parent,
    Student,
    AcademicYear,
    StudentEnrollment,
    StudentYearSummary,
    Mark,
    StudentAchievement, 
    Project,
    BookIssue,RemedialSession,
)
#from .ai import build_career_context

def get_logged_in_user(request):

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return User.objects.filter(
        id=user_id,
        role="P"
    ).first()


def get_parent(user):

    if not user:
        return None

    return Parent.objects.filter(
        unique_user_id=str(user.reg_id),
        school=user.school
    ).first()


def get_children(parent, school):

    return Student.objects.filter(
        parent=parent,
        school=school
    ).order_by(
        "first_name",
        "last_name"
    )


def get_unique_children(children):

    unique_children = []
    seen = set()

    for child in children:

        name = (
            f"{child.first_name} "
            f"{child.last_name}"
        ).strip()

        if name not in seen:

            unique_children.append({
                "name": name
            })

            seen.add(name)

    return unique_children


def get_selected_child_name(
    request,
    unique_children
):

    child_name = request.GET.get(
        "child_name"
    )

    if child_name:

        request.session[
            "child_name"
        ] = child_name

        return child_name

    child_name = request.session.get(
        "child_name"
    )

    if child_name:
        return child_name

    if unique_children:

        return unique_children[0]["name"]

    return None


def get_academic_years():

    active_year = AcademicYear.objects.filter(is_active=True).first()
    if not active_year:
        return AcademicYear.objects.none()

    return AcademicYear.objects.filter(start_date__lte=active_year.start_date).order_by("-start_date")[:5]


def get_selected_academic_year(request):

    year_id = request.GET.get(
        "academic_year_id"
    )

    if year_id:

        request.session[
            "academic_year_id"
        ] = year_id

        return year_id

    year_id = request.session.get(
        "academic_year_id"
    )

    if year_id:
        return year_id

    active_year = AcademicYear.objects.filter(
        is_active=True
    ).first()

    if active_year:
        return active_year.id

    return None


def get_student_for_year(

    parent,
    school,
    child_name,
    academic_year_id

):

    if not child_name:
        return None

    name_parts = child_name.split()

    first_name = name_parts[0]

    last_name = " ".join(
        name_parts[1:]
    )

    enrollment = (
        StudentEnrollment.objects
        .select_related(
            "student"
        )
        .filter(
            student__parent=parent,
            student__school=school,
            student__first_name=first_name,
            student__last_name=last_name,
            academic_year_id=academic_year_id
        )
        .first()
    )

    if enrollment:
        return enrollment.student

    return None


def get_enrollment(
    student,
    academic_year_id,
    school
):

    if not student:
        return None

    return (
        StudentEnrollment.objects
        .select_related(
            "division",
            "division__class_ref",
            "academic_year"
        )
        .filter(
            student=student,
            academic_year_id=academic_year_id,
            school=school
        )
        .first()
    )


def get_student_year_summary(
    enrollment
):

    if not enrollment:
        return None

    return StudentYearSummary.objects.filter(
        student_enrollment=enrollment,
        school=enrollment.school
    ).first()


def get_subject_wise_marks(enrollment):

    if not enrollment:
        return []

    subjects = OrderedDict()

    marks = Mark.objects.filter(student_enrollment=enrollment, school=enrollment.school).select_related(
        "exam_subject__exam",
        "exam_subject__subject__subject_master",
        "exam_type"
    )

    for mark in marks:

        subject_name = mark.exam_subject.subject.subject_master.name
        exam_name = mark.exam_subject.exam.name
        exam_type_name = mark.exam_type.name if mark.exam_type else "N/A"

        if subject_name not in subjects:
            subjects[subject_name] = {
                "subject_name": subject_name,
                "total_obtained": 0,
                "total_marks": 0,
                "percentage": 0,
                "exams": OrderedDict()
            }

        subject = subjects[subject_name]

        obtained = float(mark.obtained_marks or 0)
        total = float(mark.total_marks or 0)

        subject["total_obtained"] += obtained
        subject["total_marks"] += total

        if exam_name not in subject["exams"]:
            subject["exams"][exam_name] = {
                "exam_name": exam_name,
                "exam_total_obtained": 0,
                "exam_total_marks": 0,
                "exam_percentage": 0,
                "exam_types": []
            }

        exam = subject["exams"][exam_name]

        exam["exam_total_obtained"] += obtained
        exam["exam_total_marks"] += total

        exam["exam_types"].append({
            "exam_type": exam_type_name,
            "obtained": obtained,
            "total": total,
            "percentage": float(mark.percentage or 0)
        })

    result = []

    for subject in subjects.values():

        if subject["total_marks"]:
            subject["percentage"] = round((subject["total_obtained"] / subject["total_marks"]) * 100, 2)

        for exam in subject["exams"].values():
            if exam["exam_total_marks"]:
                exam["exam_percentage"] = round((exam["exam_total_obtained"] / exam["exam_total_marks"]) * 100, 2)

        subject["exams"] = list(subject["exams"].values())
        result.append(subject)

    return result

def get_class_enrollments(enrollment):

    if not enrollment:
        return StudentEnrollment.objects.none()

    return StudentEnrollment.objects.filter(
        division=enrollment.division,
        academic_year=enrollment.academic_year,
        school=enrollment.school
    ).exclude(
        id=enrollment.id
    )

def get_achievements(student, school):

    achievements = []

    student_achievements = (
        StudentAchievement.objects
        .filter(
            student=student,
            school=school
        )
        .order_by("-date")
    )

    for achievement in student_achievements:

        achievements.append({
            "title": achievement.title,
            "category": achievement.type,
            "date": (
                achievement.date.strftime("%d %b %Y")
                if achievement.date else ""
            ),
            "description": achievement.description,
            "awarded_by": "School"
        })
    return achievements




def get_remedial_data(enrollment):

    if not enrollment:
        return {
            "is_remedial": False,
            "session_count": 0,
            "subjects": [],
            "primary_remedial_subject": None,
            "primary_remedial_sessions": 0,
            "latest_note": ""
        }

    sessions = (
        RemedialSession.objects
        .filter(
            student_enrollment=enrollment,
            school=enrollment.school
        )
        .select_related(
            "subject__subject_master"
        )
        .order_by("-session_date")
    )

    if not sessions.exists():
        return {
            "is_remedial": False,
            "session_count": 0,
            "subjects": [],
            "primary_remedial_subject": None,
            "primary_remedial_sessions": 0,
            "latest_note": ""
        }

    subject_counter = Counter()

    for session in sessions:

        if (
            session.subject
            and session.subject.subject_master
        ):
            subject_name = (
                session.subject
                .subject_master
                .name
            )

            subject_counter[
                subject_name
            ] += 1

    subject_summary = []

    for subject_name, count in subject_counter.items():

        subject_summary.append({
            "subject": subject_name,
            "sessions": count
        })

    primary_subject = None
    primary_sessions = 0

    if subject_counter:

        primary_subject, primary_sessions = (
            subject_counter.most_common(1)[0]
        )

    latest_session = sessions.first()

    return {

        "is_remedial": True,

        "session_count": sessions.count(),

        "subjects": subject_summary,

        "primary_remedial_subject":
            primary_subject,

        "primary_remedial_sessions":
            primary_sessions,

        "latest_note":
            latest_session.notes or ""
    }


def get_library_data(student, school):

    issues = (
        BookIssue.objects
        .filter(
            student=student,
            school=school
        )
        .select_related("book")
        .order_by("-issue_date")
    )

    total_books = issues.count()

    active_books = 0
    book_types = []
    recent_books = []

    for issue in issues:

        if issue.return_date is None:
            active_books += 1

        if issue.book and issue.book.type:
            book_types.append(
                issue.book.type
            )

        if (
            issue.book and
            len(recent_books) < 3
        ):
            recent_books.append(
                issue.book.title
            )

    favorite_type = None

    if book_types:
        favorite_type = (
            Counter(book_types)
            .most_common(1)[0][0]
        )

    return {

        "is_reader":
            total_books > 0,

        "total_books":
            total_books,

        "active_books":
            active_books,

        "favorite_type":
            favorite_type,

        "recent_books":
            recent_books,

        "suggestion":
            None if total_books > 0
            else (
                "Encourage regular reading and library participation "
                "to support learning beyond the classroom."
            )
    }

def get_project_data(student, school):

    projects = (
        Project.objects
        .filter(
            student=student,
            school=school
        )
        .order_by("-date")
    )

    return {
        "has_projects": projects.exists(),
        "project_count": projects.count(),
        "projects": [
            {
                "title": project.title,
                "description": project.description,
                "type": project.type,
                "date": (
                    project.date.strftime("%d %b %Y")
                    if project.date else ""
                )
            }
            for project in projects
        ]
    }

def get_academic_summary(
    subject_wise_marks,
    remedial_data
):

    def get_subject_status(score):

        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Strong"
        if score >= 60:
            return "Good"
        if score >= 50:
            return "Needs Attention"

        return "Critical"

    if not subject_wise_marks:

        return {
            "top_subject": None,
            "weak_subject": None,
            "attention_area": None,
            "top_3_subjects": [],
            "bottom_3_subjects": [],
            "remedial_status": False,
            "remedial_subject": None,
            "remedial_sessions": 0
        }

    sorted_subjects = sorted(
        subject_wise_marks,
        key=lambda x: x["percentage"],
        reverse=True
    )

    top_subject = sorted_subjects[0]
    weak_subject = sorted_subjects[-1]

    top_3_subjects = [
        {
            "subject": subject["subject_name"],
            "percentage": subject["percentage"],
            "status": get_subject_status(
                subject["percentage"]
            )
        }
        for subject in sorted_subjects[:3]
    ]

    bottom_3_subjects = [
        {
            "subject": subject["subject_name"],
            "percentage": subject["percentage"],
            "status": get_subject_status(
                subject["percentage"]
            )
        }
        for subject in reversed(
            sorted_subjects[-3:]
        )
    ]

    attention_area = (
        weak_subject["subject_name"]
        if weak_subject["percentage"] < 60
        else None
    )

    return {
        "top_subject": {
            "name": top_subject["subject_name"],
            "percentage": top_subject["percentage"]
        },
        "weak_subject": {
            "name": weak_subject["subject_name"],
            "percentage": weak_subject["percentage"]
        },
        "top_3_subjects": top_3_subjects,
        "bottom_3_subjects": bottom_3_subjects,
        "attention_area": attention_area,
        "remedial_status": remedial_data["is_remedial"],
        "remedial_subject": remedial_data["primary_remedial_subject"],
        "remedial_sessions": remedial_data["primary_remedial_sessions"]
    }

def get_student_five_year_data(
    student,
    selected_year_id
):

    if not student:
        return []

    current_year = AcademicYear.objects.filter(
        id=selected_year_id
    ).first()

    if not current_year:
        return []

    years = (
        AcademicYear.objects
        .filter(
            start_date__lte=current_year.start_date
        )
        .order_by("-start_date")[:5]
    )

    student_ids = (
        Student.objects
        .filter(
            parent=student.parent,
            school=student.school,
            first_name=student.first_name,
            last_name=student.last_name
        )
        .values_list(
            "id",
            flat=True
        )
    )

    enrollments = (
        StudentEnrollment.objects
        .filter(
            student_id__in=student_ids,
            academic_year__in=years,
            school=student.school
        )
        .select_related(
            "academic_year"
        )
        .order_by(
            "academic_year__start_date"
        )
    )

    result = []

    for enrollment in enrollments:

        marks = (
            Mark.objects
            .filter(
                student_enrollment=enrollment
            )
            .select_related(
                "exam_subject__subject__subject_master"
            )
        )

        subjects = {}

        for mark in marks:

            subject_name = (
                mark.exam_subject
                .subject
                .subject_master
                .name
            )

            if subject_name not in subjects:

                subjects[subject_name] = {
                    "obtained": 0,
                    "total": 0
                }

            subjects[subject_name]["obtained"] += float(
                mark.obtained_marks or 0
            )

            subjects[subject_name]["total"] += float(
                mark.total_marks or 0
            )

        subject_scores = []

        for subject_name, values in subjects.items():

            percentage = 0

            if values["total"] > 0:

                percentage = round(
                    (
                        values["obtained"]
                        / values["total"]
                    ) * 100,
                    2
                )

            subject_scores.append({
                "subject": subject_name,
                "percentage": percentage
            })

        result.append({
            "academic_year":
                enrollment.academic_year.name,

            "student_id":
                enrollment.student_id,

            "enrollment_id":
                enrollment.id,

            "subjects":
                subject_scores
        })

    return result


def get_subject_heatmap_data(five_year_data):

    years = []
    subjects = set()
    values = []

    for year_index, year in enumerate(five_year_data):

        years.append(year["academic_year"])

        for subject_data in year["subjects"]:

            subjects.add(
                subject_data["subject"]
            )

    subjects = sorted(list(subjects))

    for year_index, year in enumerate(five_year_data):

        for subject_data in year["subjects"]:

            values.append({
                "x": year["academic_year"],
                "y": subject_data["subject"],
                "v": subject_data["percentage"]
            })

    return {
        "years": years,
        "subjects": subjects,
        "values": values
    }



def get_subject_growth_journey(student, selected_year_id):

    result = {
        "subjects": [],
        "top_performer": None,
        "top_improving_subject": None,
        "top_declining_subject": None,
        "most_consistent_subject": None,
        "best_retained_subject": None,
        "weak_subject": None,
        "improved_subject_count": 0,
        "stable_subject_count": 0,
        "declining_subject_count": 0,
        "growth_summary": ""
    }

    five_year_data = get_student_five_year_data(
        student,
        selected_year_id,
        
    )

    if not five_year_data:
        return result

    subject_history = {}

    for year_data in five_year_data:
        for subject in year_data["subjects"]:

            subject_name = subject["subject"]

            if subject_name not in subject_history:
                subject_history[subject_name] = []

            subject_history[subject_name].append(
                subject["percentage"]
            )

    for subject_name, scores in subject_history.items():

        current_score = scores[-1]
        first_score = scores[0]

        growth = round(
            current_score - first_score,
            2
        )

        score_range = round(
            max(scores) - min(scores),
            2
        )

        years_present = len(scores)

        if growth >= 5:
            trend = "Strong Growth"
        elif growth > 0:
            trend = "Improving"
        elif growth >= -5:
            trend = "Stable"
        else:
            trend = "Declining"

        if current_score >= 85:
            performance_band = "Excellent"
        elif current_score >= 70:
            performance_band = "Strong"
        elif current_score >= 60:
            performance_band = "Good"
        else:
            performance_band = "Needs Attention"

        result["subjects"].append({
            "subject": subject_name,
            "current_score": current_score,
            "first_score": first_score,
            "five_year_growth": growth,
            "history": scores,
            "years_present": years_present,
            "score_range": score_range,
            "trend": trend,
            "performance_band": performance_band
        })

    if not result["subjects"]:
        return result

    result["top_performer"] = max(
        result["subjects"],
        key=lambda x: x["current_score"]
    )

    result["weak_subject"] = min(
        result["subjects"],
        key=lambda x: x["current_score"]
    )

    result["most_consistent_subject"] = min(
        result["subjects"],
        key=lambda x: x["score_range"]
    )

    positive_subjects = [
        s for s in result["subjects"]
        if s["five_year_growth"] > 0
    ]

    declining_subjects = [
        s for s in result["subjects"]
        if s["five_year_growth"] < -5
    ]

    stable_subjects = [
        s for s in result["subjects"]
        if -5 <= s["five_year_growth"] <= 5
    ]

    result["improved_subject_count"] = len(positive_subjects)
    result["stable_subject_count"] = len(stable_subjects)
    result["declining_subject_count"] = len(declining_subjects)

    if declining_subjects:
        result["top_declining_subject"] = min(
            declining_subjects,
            key=lambda x: x["five_year_growth"]
        )

    if positive_subjects:

        result["top_improving_subject"] = max(
            positive_subjects,
            key=lambda x: x["five_year_growth"]
        )

        result["best_retained_subject"] = result[
            "most_consistent_subject"
        ]

        result["growth_summary"] = (
            f"{result['top_improving_subject']['subject']} "
            f"shows the strongest long-term improvement with a "
            f"growth of {result['top_improving_subject']['five_year_growth']} "
            f"percentage points. "
            f"{result['top_performer']['subject']} remains the "
            f"highest performing subject currently."
        )

    else:

        result["top_improving_subject"] = result[
            "top_performer"
        ]

        result["best_retained_subject"] = result[
            "most_consistent_subject"
        ]

        result["growth_summary"] = (
            f"No subject has shown overall positive growth across "
            f"the selected academic period. "
            f"{result['top_performer']['subject']} remains the "
            f"strongest performing subject with "
            f"{result['top_performer']['current_score']}%. "
            f"{result['most_consistent_subject']['subject']} has "
            f"shown the most stable performance over the years."
        )

    return result





def get_learning_rhythm(library_data, subject_growth_journey, remedial_data, project_data):

    strengths = []
    concerns = []

    if library_data["is_reader"]:

        strengths.append({
            "type": "reading",
            "books_read": library_data["total_books"],
            "favorite_type": library_data["favorite_type"]
        })

    top_growth = (
        subject_growth_journey.get(
            "top_improving_subject"
        )
    )

    if top_growth:

        strengths.append({
            "type": "academic_growth",
            "subject": top_growth["subject"],
            "growth": top_growth["five_year_growth"]
        })

    if project_data["project_count"] > 0:

        strengths.append({
            "type": "projects",
            "count": project_data["project_count"]
        })

    weak_subject = (
        subject_growth_journey.get(
            "weak_subject"
        )
    )

    if weak_subject:

        concerns.append({
            "type": "weak_subject",
            "subject": weak_subject["subject"],
            "score": weak_subject["current_score"]
        })

    declining_subject = (
        subject_growth_journey.get(
            "top_declining_subject"
        )
    )

    if declining_subject:

        concerns.append({
            "type": "declining_subject",
            "subject": declining_subject["subject"],
            "decline": abs(
                declining_subject["five_year_growth"]
            )
        })

    if remedial_data["is_remedial"]:

        concerns.append({
            "type": "remedial",
            "subject": remedial_data[
                "primary_remedial_subject"
            ],
            "sessions": remedial_data[
                "primary_remedial_sessions"
            ]
        })

    return {

        "reading_profile": {
            "is_reader":
                library_data["is_reader"],

            "books_read":
                library_data["total_books"],

            "active_books":
                library_data["active_books"],

            "favorite_type":
                library_data["favorite_type"]
        },

        "project_engagement": {
            "project_count":
                project_data["project_count"],

            "has_projects":
                project_data["has_projects"]
        },

        "strengths":
            strengths,

        "concerns":
            concerns
    }






def parent_dashboard(request): 

    user = get_logged_in_user(
        request
    )

    if not user:
        return redirect("/")

    parent = get_parent(user)

    if not parent:

        return render(
            request,
            "parent/dashboard.html",
            {
                "error":
                "Parent not found"
            }
        )

    children = get_children(
        parent,
        user.school
    )

    if not children.exists():

        return render(
            request,
            "parent/dashboard.html",
            {
                "error":
                "No students found"
            }
        )

    unique_children = get_unique_children(
        children
    )

    selected_child_name = (
        get_selected_child_name(
            request,
            unique_children
        )
    )

    academic_years = (
        get_academic_years()
    )

    selected_year_id = (
        get_selected_academic_year(
            request
        )
    )

    child = get_student_for_year(
        parent,
        user.school,
        selected_child_name,
        selected_year_id
    )

    enrollment = get_enrollment(
        child,
        selected_year_id,
        user.school
    )

    summary = get_student_year_summary(
        enrollment
    )
    
    subject_wise_marks = get_subject_wise_marks(
        enrollment
    )

    subject_wise_marks_json = json.dumps(
        subject_wise_marks
    )

    subject_performance_analytics = (
        get_subject_performance_analytics(
            subject_wise_marks
        )
    )

    subject_performance_analytics_json = json.dumps(
        subject_performance_analytics
    )

    subject_growth_analytics = (
        get_subject_growth_analytics(
            subject_wise_marks
        )
    )

    subject_growth_analytics_json = json.dumps(
        subject_growth_analytics
    )






    achievements = get_achievements(
        child,
        user.school
    )

    achievements_json = json.dumps(
        achievements
    )

    library_data = get_library_data(
        child,
        user.school
    )

    library_data_json = json.dumps(
        library_data
    )


    remedial_data = get_remedial_data(
        enrollment
    )

    remedial_data_json = json.dumps(
        remedial_data
    )

    project_data = get_project_data(
        child,
        user.school
    )

    project_data_json = json.dumps(
        project_data
    )

    academic_summary = (
        get_academic_summary(
            subject_wise_marks,
            remedial_data
        )
    )

    academic_summary_json = json.dumps(
        academic_summary
    )


    subject_growth_journey = (
        get_subject_growth_journey(
            child,
            selected_year_id
        )
    )

    subject_growth_journey_json = json.dumps(
        subject_growth_journey
    )


    learning_rhythm = (
        get_learning_rhythm(
            library_data,
            subject_growth_journey,
            remedial_data,
            project_data
        )
    )

    learning_rhythm_json = json.dumps(
        learning_rhythm
    )

    five_year_data = get_student_five_year_data(
        child,
        selected_year_id
    )

    five_year_data_json = json.dumps(
        five_year_data
    )

    subject_heatmap = (
        get_subject_heatmap_data(
            five_year_data
        )
    )

    subject_heatmap_json = json.dumps(
        subject_heatmap
    )



    print("\n========== FIVE YEAR DATA ==========")
    print(json.dumps(
        five_year_data,
        indent=4
    ))
    print("===================================\n")
    

    return render(
        request,
        "parent/dashboard.html",
        {

            "parent":
            parent,

            "children":
            unique_children,

            "child":
            child,

            "academic_years":
            academic_years,

            "selected_child_name":
            selected_child_name,

            "selected_year_id":
            int(selected_year_id)
            if selected_year_id
            else None,

            "enrollment":
            enrollment,

            "summary":
            summary,

            "subject_wise_marks":
            subject_wise_marks,

            "subject_wise_marks_json": 
            subject_wise_marks_json,

            "subject_performance_analytics": 
            subject_performance_analytics,

            "subject_performance_analytics_json": 
            subject_performance_analytics_json,

            "subject_growth_analytics":
            subject_growth_analytics,

            "subject_growth_analytics_json":
            subject_growth_analytics_json,

            "achievements":
            achievements,

            "achievements_json":
            achievements_json,

            "library_data":
            library_data,

            "library_data_json":
            library_data_json,

            "remedial_data":
            remedial_data,

            "remedial_data_json":
            remedial_data_json,

            "project_data":
            project_data,

            "project_data_json":
            project_data_json,

            "academic_summary":
            academic_summary,

            "academic_summary_json":
            academic_summary_json,

            "subject_growth_journey":
            subject_growth_journey,

            "subject_growth_journey_json":
            subject_growth_journey_json,

            "learning_rhythm":
            learning_rhythm,

            "learning_rhythm_json":
            learning_rhythm_json,

            "five_year_data":
            five_year_data,

            "five_year_data_json":
            five_year_data_json,

            "subject_heatmap":
            subject_heatmap,

            "subject_heatmap_json":
            subject_heatmap_json,

            "std":
            (
                enrollment.division.class_ref.name
                if enrollment
                and enrollment.division
                and enrollment.division.class_ref
                else ""
            ),

            "division":
            (
                enrollment.division.name
                if enrollment
                and enrollment.division
                else ""
            ),

            "roll_number":
            (
                enrollment.roll_number
                if enrollment
                else ""
            ),

            "overall_score":
            (
                summary.avg_marks
                if summary
                else 0
            ),

            "days_present":
            (
                summary.attendance_percentage
                if summary
                else 0
            ),

            "father_name":
            parent.father_name,

            "mother_name":
            parent.mother_name,

            "guardian":
            "",

            "phone":
            ", ".join(
                filter(
                    None,
                    [
                        parent.father_phone,
                        parent.mother_phone
                    ]
                )
            )
        }
    )