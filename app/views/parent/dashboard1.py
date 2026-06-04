from django.shortcuts import render, redirect 
from app.models import(
    User, Parent, Student, StudentEnrollment, StudentYearSummary, AcademicYear  
)
 # Helpers 

def get_logged_in_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None 
    
    return User.objects.filter(id=user_id, role="P").first()

def get_parent(user):
    if not user:
        return None
    
    return Parent.objects.filter(unique_user_id=str(user.reg_id), school=user.school).first()


def get_children(parent, school):
    if not parent:
        return Student.objects.none()
    
    return Student.objects.filter(parent_id = parent.id, school=school).order_by("first_name", "last_name")

def get_selected_student(children, student_id):
    if student_id: 
        child=children.filter(id=student_id).first()

        if child:
            return child
    return children.first()

def get_academic_years(child):
    if not child:
        return AcademicYear.objects.none()
    return AcademicYear.objects.filter(studentenrollment_student=child).distinct().order_by("-start_date")

def get_selected_academic_year(request,academic_years):
    session_year_id = request.session.get("academic_year_id")
    selected_year_id = request.Get.get("academic_year_id")

    if selected_year_id:
        request.session["academic_year_id"] = selected_year_id
        return selected_year_id
    
    if session_year_id:
        return session_year_id
    
    if academic_years.exists():
        return academic_years.first().id
    return None






# Dashboard main function 

def parent_dashboard(request):


