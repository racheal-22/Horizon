# app/views.py

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password

from app.models import User


@csrf_exempt
def login_view(request):

    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "Only POST method allowed"
        })

    try:
        body = json.loads(request.body)

        email = body.get("email")
        password = body.get("password")
        school_id = body.get("school_id")

        # validations
        if not email:
            return JsonResponse({
                "status": False,
                "message": "Email is required"
            })

        if not password:
            return JsonResponse({
                "status": False,
                "message": "Password is required"
            })

        if not school_id:
            return JsonResponse({
                "status": False,
                "message": "School ID is required"
            })

        # find user
        try:
            user = User.objects.get(
                email=email,
                school_id=school_id
            )

        except User.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "User not found"
            })

        # verify hashed password
        is_valid_password = check_password(
            password,
            user.password
        )

        if not is_valid_password:
            return JsonResponse({
                "status": False,
                "message": "Invalid password"
            })

        # create session
        request.session["user_id"] = user.id
        request.session["role"] = user.role
        request.session["school_id"] = user.school_id

        # dashboard mapping
        role_dashboard = {
            "T": "/teacher/dashboard/",
            "P": "/parent/dashboard/",
            "M": "/principal/dashboard/"
        }

        return JsonResponse({
            "status": True,
            "message": "Login successful",
            "data": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "redirect_url": role_dashboard.get(user.role)
            }
        })

    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": str(e)
        })