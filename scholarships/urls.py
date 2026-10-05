from django.urls import path

from .views import scholarship_detail

urlpatterns = [
    path("<int:pk>/", scholarship_detail, name="scholarship-detail"),
]
