from collections import OrderedDict
from app.models import (
    StudentEnrollment,
    AcademicYear,
    StudentYearSummary,
)


def get_subject_performance_analytics(subject_wise_marks):
    if not subject_wise_marks:
        return {}
    
    sorted_subjects = sorted(subject_wise_marks, key=lambda x: x['percentage'], reverse=True)
    
    strongest_subject = sorted_subjects[0] 
    weakest_subject = sorted_subjects[-1] 

    return {

        "labels": [
            subject["subject_name"]
            for subject in sorted_subjects
        ],

        "scores": [
            subject["percentage"]
            for subject in sorted_subjects
        ],

        "strongest_subject":
            strongest_subject["subject_name"],

        "strongest_score":
            strongest_subject["percentage"],

        "weakest_subject":
            weakest_subject["subject_name"],

        "weakest_score":
            weakest_subject["percentage"],

        "subject_gap":
            round(
                strongest_subject["percentage"]
                - weakest_subject["percentage"],
                2
            )
    }


def get_subject_growth_analytics(subject_wise_marks):

    if not subject_wise_marks:
        return []

    growth_data = []

    for subject in subject_wise_marks:

        term_scores = []

        for exam in subject["exams"]:

            term_scores.append({
                "term": exam["exam_name"],
                "percentage": exam["exam_percentage"]
            })

        growth_data.append({
            "subject": subject["subject_name"],
            "terms": term_scores
        })

    return growth_data



def get_academic_comparison_analytics(
    enrollment
):

    if not enrollment:
        return []

    summaries = (
        StudentYearSummary.objects
        .select_related(
            "student_enrollment__student"
        )
        .filter(
            student_enrollment__division=
                enrollment.division,

            student_enrollment__academic_year=
                enrollment.academic_year,

            school=enrollment.school
        )
        .order_by("avg_marks")
    )

    data = []

    for summary in summaries:

        student = (
            summary.student_enrollment.student
        )

        data.append({
            "student_name":
                f"{student.first_name} {student.last_name}".strip(),

            "overall_percentage":
                float(summary.avg_marks or 0),

            "is_current":
                summary.student_enrollment_id
                == enrollment.id
        })

    return data



def get_yearly_trend_analytics(
    student,
    selected_year_id
):

    if not student:
        return []

    current_year = (
        AcademicYear.objects
        .filter(id=selected_year_id)
        .first()
    )

    if not current_year:
        return []

    year_ids = (
        AcademicYear.objects
        .filter(
            start_date__lte=current_year.start_date
        )
        .order_by("-start_date")
        .values_list("id", flat=True)[:5]
    )

    summaries = (
        StudentYearSummary.objects
        .select_related(
            "student_enrollment__academic_year"
        )
        .filter(
            student_enrollment__student=student,
            student_enrollment__academic_year_id__in=year_ids
        )
        .order_by(
            "student_enrollment__academic_year__start_date"
        )
    )

    trend_data = []

    for summary in summaries:

        trend_data.append({
            "label":
                summary.student_enrollment
                .academic_year
                .name,

            "percentage":
                round(
                    float(summary.avg_marks or 0),
                    2
                )
        })

    return trend_data
