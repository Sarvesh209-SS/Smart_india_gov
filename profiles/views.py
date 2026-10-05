from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import UserProfile


@login_required
def profile_form(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.full_name = request.POST.get("full_name", profile.full_name)
        profile.date_of_birth = request.POST.get("date_of_birth") or None
        profile.state = request.POST.get("state", "")
        profile.district = request.POST.get("district", "")
        profile.education_level = request.POST.get("education_level", "")
        profile.course = request.POST.get("course", "")
        profile.institution = request.POST.get("institution", "")
        profile.category = request.POST.get("category", "")
        income = request.POST.get("annual_family_income")
        profile.annual_family_income = int(income) if income else None
        first_gen = request.POST.get("first_generation_graduate")
        profile.first_generation_graduate = first_gen == "on"
        profile.save()
        language = request.POST.get("preferred_language")
        if language in {choice[0] for choice in settings.LANGUAGES}:
            request.user.preferred_language = language
            request.user.save(update_fields=["preferred_language"])
            request.session["django_language"] = language
        return redirect("dashboard")

    return render(request, "profile.html", {"profile": profile})
