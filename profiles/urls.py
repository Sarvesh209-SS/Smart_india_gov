from django.urls import path
from .views import profile_form

urlpatterns = [
    path("", profile_form, name="profile"),
]
