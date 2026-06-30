from collections import Counter


def build_career_context(
    child,
    summary,
    academic_summary,
    subject_growth_journey,
    learning_rhythm,
    library_data,
    project_data,
    achievements,
    remedial_data,
    subject_wise_marks,
    five_year_data=None,
    subject_heatmap=None,
):

    top_subjects = [
        subject["subject"]
        for subject in academic_summary.get("top_3_subjects", [])
    ]

    weak_subjects = [
        subject["subject"]
        for subject in academic_summary.get("bottom_3_subjects", [])
    ]

    improving_subject = None

    if subject_growth_journey.get("top_improving_subject"):
        improving_subject = (
            subject_growth_journey["top_improving_subject"]["subject"]
        )

    declining_subject = None

    if subject_growth_journey.get("top_declining_subject"):
        declining_subject = (
            subject_growth_journey["top_declining_subject"]["subject"]
        )

    consistent_subject = None

    if subject_growth_journey.get("most_consistent_subject"):
        consistent_subject = (
            subject_growth_journey["most_consistent_subject"]["subject"]
        )

    achievement_categories = []

    for achievement in achievements:
        if achievement.get("category"):
            achievement_categories.append(
                achievement["category"]
            )

    career_context = {

        "student": {

            "name": (
                f"{child.first_name} "
                f"{child.last_name}"
            ),

            "overall_score":
                summary.avg_marks if summary else 0,

            "attendance":
                summary.attendance_percentage if summary else 0,

        },

        "academic": {

            "top_subject":
                academic_summary.get("top_subject"),

            "weak_subject":
                academic_summary.get("weak_subject"),

            "top_subjects":
                top_subjects,

            "weak_subjects":
                weak_subjects,

            "subject_marks":
                subject_wise_marks,
        },

        "growth": {

            "improving_subject":
                improving_subject,

            "declining_subject":
                declining_subject,

            "consistent_subject":
                consistent_subject,

            "growth_summary":
                subject_growth_journey.get(
                    "growth_summary"
                ),
        },

        "learning": {

            "reading_profile":
                learning_rhythm.get(
                    "reading_profile"
                ),

            "project_engagement":
                learning_rhythm.get(
                    "project_engagement"
                ),

            "strengths":
                learning_rhythm.get(
                    "strengths"
                ),

            "concerns":
                learning_rhythm.get(
                    "concerns"
                ),
        },

        "library": library_data,

        "projects": project_data,

        "achievements": {

            "count":
                len(achievements),

            "categories":
                achievement_categories,

            "details":
                achievements,
        },

        "remedial": remedial_data,

        "five_year_history":
            five_year_data,

        "heatmap":
            subject_heatmap,
    }

    return career_context


def build_career_profile(career_context):

    profile = {

        "analytical_score": 0,

        "technical_score": 0,

        "research_score": 0,

        "communication_score": 0,

        "leadership_score": 0,

        "creativity_score": 0,

        "discipline_score": 0,

        "teamwork_score": 0,

        "career_strengths": [],

        "career_concerns": []
    }

    return profile

