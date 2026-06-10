
from django.shortcuts import render, redirect
from collections import OrderedDict

from app.models import (
    User,
    Parent,
    Student,
    AcademicYear,
    StudentEnrollment,
    StudentYearSummary,
    Mark,
)


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
        student_enrollment=enrollment
    ).first()


def get_subject_wise_marks(enrollment):

    if not enrollment:
        return []

    subjects = OrderedDict()

    marks = Mark.objects.filter(student_enrollment=enrollment).select_related(
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