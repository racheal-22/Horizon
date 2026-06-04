from django.shortcuts import render, redirect
 
from app.models import (
    User,
    Parent,
    Student,
    StudentEnrollment,
    StudentYearSummary,
    AcademicYear
)


def parent_dashboard(request):

    user_id = request.session.get("user_id")
    default_academic_year_id = request.session.get("academic_year_id")

    if not user_id:
        return redirect("/")

    user = User.objects.filter(
        id=user_id,
        role="P"
    ).first()

    if not user:
        return redirect("/")

    parent = Parent.objects.filter(
        unique_user_id=str(user.reg_id),
        school=user.school
    ).first()

    if not parent:
        return render(
            request,
            "parent/dashboard.html",
            {
                "error": "Parent not found"
            }
        )

    # ==========================
    # ALL CHILDREN OF PARENT
    # ==========================

    children = Student.objects.filter(
        parent=parent,
        school=user.school
    ).order_by(
        "first_name",
        "last_name"
    )

    if not children.exists():
        return render(
            request,
            "parent/dashboard.html",
            {
                "error": "No students found",
                "parent": parent
            }
        )

    # ==========================
    # SELECTED CHILD
    # ==========================

    selected_student_id = request.GET.get("student_id")

    if selected_student_id:

        child = children.filter(
            id=selected_student_id
        ).first()

        if not child:
            child = children.first()

    else:
        child = children.first()

    # ==========================
    # ACADEMIC YEARS FOR CHILD
    # ==========================

    academic_years = AcademicYear.objects.filter(
        studentenrollment__student=child
    ).distinct().order_by("-start_date")

    selected_year_id = request.GET.get(
        "academic_year_id",
        default_academic_year_id
    )

    if not selected_year_id and academic_years.exists():
        selected_year_id = academic_years.first().id

    # ==========================
    # ENROLLMENT
    # ==========================

    enrollment = StudentEnrollment.objects.select_related(
        "division",
        "division__class_ref",
        "academic_year"
    ).filter(
        student=child,
        academic_year_id=selected_year_id,
        student__school=user.school
    ).first()

    # ==========================
    # SUMMARY
    # ==========================

    summary = None

    if enrollment:

        summary = StudentYearSummary.objects.filter(
            student_enrollment=enrollment
        ).first()

    # ==========================
    # RESPONSE
    # ==========================

    return render(
        request,
        "parent/dashboard.html",
        {
            "parent": parent,

            "children": children,

            "child": child,

            "selected_student_id": child.id,

            "academic_years": academic_years,

            "selected_year_id": (
                int(selected_year_id)
                if selected_year_id
                else None
            ),

            "enrollment": enrollment,

            "summary": summary,

            "overall_score": (
                summary.avg_marks
                if summary
                else 0
            ),

            "days_present": (
                summary.attendance_percentage
                if summary
                else 0
            ),

            "std": (
                enrollment.division.class_ref.name
                if enrollment
                and enrollment.division
                and enrollment.division.class_ref
                else ""
            ),

            "division": (
                enrollment.division.name
                if enrollment
                and enrollment.division
                else ""
            ),

            "academic_year": (
                enrollment.academic_year.name
                if enrollment
                and enrollment.academic_year
                else ""
            ),

            "father_name": parent.father_name,

            "mother_name": parent.mother_name,

            "guardian": "",

            "phone": ", ".join(
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