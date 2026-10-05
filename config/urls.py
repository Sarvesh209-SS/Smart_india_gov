from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import include, path
from documents.views import download_document


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("documents/", include("documents.urls")),
    path("profile/", include("profiles.urls")),
    path("scholarships/", include("scholarships.urls")),
    path("admin/", admin.site.urls),
    path("documents/<int:pk>/download/", download_document, name="doc-download"),
]
