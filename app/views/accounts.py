from passlib.hash import bcrypt

from django.shortcuts import render,redirect

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from app.models import User,AcademicYear
from app.serializers.accounts import LoginSerializer
from app.authentication import CustomJWTAuthentication


# =========================================================
# API LOGIN
# =========================================================

class LoginView(APIView):

    authentication_classes=[]
    permission_classes=[]

    def post(self,request):

        serializer=LoginSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "status":False,
                    "errors":serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        username=serializer.validated_data.get(
            "username"
        )

        password=serializer.validated_data.get(
            "password"
        )

        user=User.objects.filter(
            email=username
        ).first()

        if not user:

            return Response(
                {
                    "status":False,
                    "message":"Invalid username"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            password_valid=bcrypt.verify(
                password,
                user.password
            )

        except Exception as e:

            return Response(
                {
                    "status":False,
                    "message":str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not password_valid:

            return Response(
                {
                    "status":False,
                    "message":"Invalid password"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh=RefreshToken.for_user(user)

        active_year=AcademicYear.objects.filter(
            school=user.school,
            is_active=True
        ).first()

        previous_years=AcademicYear.objects.filter(
            school=user.school,
            is_active=False,
            start_date__lt=active_year.start_date
        ).order_by("-start_date")[:5]

        academic_years=[active_year]+list(previous_years)

        academic_year_data=[
            {
                "id":year.id,
                "name":year.name,
                "is_active":year.is_active
            }
            for year in academic_years
        ]

        return Response(
            {
                "status":True,

                "tokens":{

                    "access":
                    str(refresh.access_token),

                    "refresh":
                    str(refresh)
                },

                "data":{

                    "id":user.id,

                    "name":user.name,

                    "email":user.email,

                    "role":user.role,

                    "academic_years":academic_year_data
                }
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# ME API
# =========================================================

class MeView(APIView):

    authentication_classes=[
        CustomJWTAuthentication
    ]

    permission_classes=[
        IsAuthenticated
    ]

    def get(self,request):

        user=request.user

        return Response(
            {
                "status":True,

                "data":{

                    "id":user.id,

                    "name":user.name,

                    "email":user.email,

                    "role":user.role
                }
            }
        )

# =========================================================
# UI LOGIN PAGE
# =========================================================

def login_page(request):

    tab = request.POST.get("tab") or "Parent"

    academic_years = AcademicYear.objects.order_by(
        "-start_date"
    )[:6]

    # =========================================
    # GET PAGE
    # =========================================

    if request.method == "GET":

        return render(
            request,
            "accounts/login.html",
            {
                "tab": tab,
                "academic_years": academic_years
            }
        )

    # =========================================
    # TAB SWITCH
    # =========================================

    if request.method == "POST" and not request.POST.get("action"):

        return render(
            request,
            "accounts/login.html",
            {
                "tab": tab,
                "academic_years": academic_years
            }
        )

    # =========================================
    # LOGIN
    # =========================================

    user_id = request.POST.get("user_id")

    password = request.POST.get("password")

    role_map = {

        "Parent": "P",

        "Teacher": "T",

        "Principal": "PR",

        "Admin": "A"
    }

    user = User.objects.filter(
        email=user_id,
        role=role_map.get(tab)
    ).first()

    if not user:

        return render(
            request,
            "accounts/login.html",
            {
                "tab": tab,
                "error": "Invalid User",
                "academic_years": academic_years
            }
        )

    try:

        password_valid = bcrypt.verify(
            password,
            user.password
        )

    except Exception as e:

        return render(
            request,
            "accounts/login.html",
            {
                "tab": tab,
                "error": str(e),
                "academic_years": academic_years
            }
        )

    if not password_valid:

        return render(
            request,
            "accounts/login.html",
            {
                "tab": tab,
                "error": "Invalid Password",
                "academic_years": academic_years
            }
        )

    selected_year_id = request.POST.get(
        "academic_year_id"
    )

    selected_year = AcademicYear.objects.filter(
        id=selected_year_id
    ).first()

    request.session["user_id"] = user.id

    request.session["name"] = user.name

    request.session["role"] = user.role

    if selected_year:

        request.session["academic_year_id"] = selected_year.id

        request.session["academic_year_name"] = selected_year.name

    if user.role == "A":

        return redirect("/admin-dashboard/")

    elif user.role == "PR":

        return redirect("/principal-dashboard/")

    elif user.role == "T":

        return redirect("/teacher-dashboard/")

    else:

        return redirect("/parent-dashboard/")

