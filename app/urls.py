from django.urls import path

from app.views.accounts import *
from app.views.parent.dashboard import parent_dashboard

urlpatterns = [

    path("", login_page, name="login"),
    path("api/login/", LoginView.as_view(), name="api_login"),
    path("api/me/", MeView.as_view(), name="me"),
    path("parent-dashboard/", parent_dashboard, name="parent_dashboard"),

]