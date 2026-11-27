from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError

from .models import User


class _SystemAdminStaffMixin:
    """Enforce the invariant ``is_staff == (role == SYSTEM_ADMINISTRATOR)``.

    Applied to both the add and change admin forms so the rule holds whether
    a user is created or edited through Django admin. ``is_superuser`` and
    every other flag are left untouched.
    """

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        # ``is_staff`` is cleaned before ``role`` alphabetically, so the
        # cross-field invariant must run at form level after every field
        # has been cleaned.
        if cleaned.get("is_staff") and role != User.Role.SYSTEM_ADMINISTRATOR:
            if role == self.instance.role:
                # Trying to grant staff to an already non-admin account.
                self.add_error(
                    "is_staff",
                    ValidationError(
                        "Only System Administrator accounts may hold staff "
                        "status. Set the role to System Administrator or "
                        "clear staff status."
                    ),
                )
            # Else: the role is being changed away from SYSTEM_ADMINISTRATOR;
            # the demotion clears staff access on the same save (see save()).
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = user.role == User.Role.SYSTEM_ADMINISTRATOR
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserAdminChangeForm(_SystemAdminStaffMixin, UserChangeForm):
    pass


class UserAdminAddForm(_SystemAdminStaffMixin, AdminUserCreationForm):
    pass


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminAddForm

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "is_active",
    ]
    list_filter = ["role", "is_staff", "is_active"]
    fieldsets = UserAdmin.fieldsets + (("Custom Fields", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Custom Fields", {"fields": ("role",)}),
    )
