
from django.shortcuts import render


def teacher_dashboard(request):

    user_name = request.session.get("name")

    return render(
        request,
        "teacher/dashboard.html",
        {
            "name": user_name
        }
    )

