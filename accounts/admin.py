from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import AuditEvent, User


class UserAdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "mobile", "role", "is_staff", "is_superuser")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def clean(self):
        return super().clean()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if user.is_superuser:
            user.role = "SUPER_ADMIN"
        if commit:
            user.save()
        return user


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserAdminCreationForm
    form = UserAdminChangeForm
    ordering = ("email",)
    list_display = ("email", "mobile_display", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "mobile", "first_name", "last_name")
    readonly_fields = ("email_verified", "last_login", "date_joined", "auth_version")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Student details", {"fields": ("first_name", "last_name", "mobile", "email_verified", "preferred_language")}),
        ("Access", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Security", {"fields": ("auth_version", "last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "mobile", "role", "is_staff", "is_superuser", "password1", "password2")}),
    )

    def save_model(self, request, obj, form, change):
        role_changed = change and ({"role", "is_staff", "is_superuser"} & set(form.changed_data))
        super().save_model(request, obj, form, change)
        if role_changed:
            AuditEvent.objects.create(user=request.user, subject=obj, event="ROLE_UPDATED")

    def has_module_permission(self, request):
        return request.user.is_superuser and request.user.role == "SUPER_ADMIN"

    @admin.display(description="Mobile")
    def mobile_display(self, obj):
        return obj.masked_mobile

    def has_view_permission(self, request, _obj=None):
        del _obj
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, _obj=None):
        del _obj
        return self.has_module_permission(request)

    def has_delete_permission(self, request, _obj=None):
        del _obj
        return self.has_module_permission(request)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "created_at")
    list_filter = ("event", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("event", "user", "created_at")

    def has_module_permission(self, request):
        return request.user.is_superuser and request.user.role == "SUPER_ADMIN"

    def has_add_permission(self, request):
        del request
        return False

    def has_change_permission(self, _request, _obj=None):
        del _request, _obj
        return False

    def has_delete_permission(self, request, _obj=None):
        del _obj
        return self.has_module_permission(request)
