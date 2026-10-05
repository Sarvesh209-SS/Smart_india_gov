from django.urls import path
from django.contrib.auth import views as auth_views
from .auth_views import logout_all_devices, security_dashboard, set_language
from .views import dashboard, register

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    path("register/", register, name="register"),
    path("dashboard/", dashboard, name="dashboard"),
    path("security/", security_dashboard, name="security-dashboard"),
    path("logout-all/", logout_all_devices, name="logout-all"),
    path("language/", set_language, name="set-language"),
]
