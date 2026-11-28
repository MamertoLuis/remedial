from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from users.forms import UserUpdateForm

User = get_user_model()


class UserRoleChoicesTests(TestCase):
    """Test the role field choices on the custom User model."""

    def test_all_four_role_values_exist(self):
        """The four role values are available as choices."""
        role_values = [choice[0] for choice in User.Role.choices]
        self.assertEqual(
            role_values,
            [
                User.Role.ACCOUNT_OFFICER,
                User.Role.MANAGER,
                User.Role.BOARD_MEMBER,
                User.Role.SYSTEM_ADMINISTRATOR,
            ],
        )
        self.assertEqual(User.Role.values, ["ACCOUNT_OFFICER", "MANAGER", "BOARD_MEMBER", "SYSTEM_ADMINISTRATOR"])

    def test_default_role_is_account_officer(self):
        """A new user defaults to the ACCOUNT_OFFICER role."""
        user = User.objects.create_user(
            username="role-default", password="password123"
        )
        self.assertEqual(user.role, User.Role.ACCOUNT_OFFICER)

    def test_system_administrator_role_assignable(self):
        """The SYSTEM_ADMINISTRATOR role can be assigned to a user."""
        user = User.objects.create_user(
            username="role-admin", password="password123"
        )
        user.role = User.Role.SYSTEM_ADMINISTRATOR
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.SYSTEM_ADMINISTRATOR)


class UserUpdateFormTests(TestCase):
    """The self-service profile form must not expose a role control."""

    def test_profile_form_exposes_only_profile_fields(self):
        """The profile form carries exactly first_name, last_name, and email."""
        user = User.objects.create_user(
            username="profile-form", password="password123"
        )
        form = UserUpdateForm(instance=user)
        self.assertEqual(
            list(form.fields.keys()),
            ["first_name", "last_name", "email"],
        )
        self.assertNotIn("role", form.fields)


class ProfileViewTests(TestCase):
    """Role changes through the self-service profile page have no effect."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="officer",
            password="password123",
            role=User.Role.ACCOUNT_OFFICER,
        )
        self.client.force_login(self.user)

    def test_loan_officer_cannot_change_own_role_via_profile_post(self):
        """POSTing a role with the profile form never changes the role."""
        for attempted_role in (User.Role.MANAGER, User.Role.SYSTEM_ADMINISTRATOR):
            with self.subTest(role=attempted_role):
                response = self.client.post(
                    reverse("profile"),
                    {"first_name": "Joe", "role": attempted_role},
                )
                self.assertRedirects(response, reverse("profile"))
                self.user.refresh_from_db()
                self.assertEqual(self.user.role, User.Role.ACCOUNT_OFFICER)
                self.assertEqual(self.user.first_name, "Joe")

    def test_profile_page_renders_no_role_control(self):
        """The profile page shows the role read-only, with no role input."""
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        # Read-only Account Info panel still shows the role value.
        self.assertContains(response, "Account Officer")
        # No role control is rendered in the form.
        self.assertNotContains(response, 'name="role"')


class UserAdminRoleStaffInvariantTests(TestCase):
    """Django admin enforces is_staff == (role == SYSTEM_ADMINISTRATOR)."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="superadmin", email="", password="password123"
        )
        self.client.force_login(self.admin)

    def _change_payload(self, user, **overrides):
        """Build a valid POST body for the Django admin user change form."""

        def _split(value):
            if not value:
                return ("", "")
            return (value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S"))

        joined_0, joined_1 = _split(user.date_joined)
        login_0, login_1 = _split(user.last_login)
        data = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_active": "on" if user.is_active else "",
            "is_staff": "on" if user.is_staff else "",
            "is_superuser": "on" if user.is_superuser else "",
            "role": user.role,
            "date_joined_0": joined_0,
            "date_joined_1": joined_1,
            "last_login_0": login_0,
            "last_login_1": login_1,
        }
        data.update(overrides)
        return data

    def test_non_admin_account_cannot_be_saved_as_staff(self):
        """Saving a non-admin account with is_staff is rejected."""
        officer = User.objects.create_user(
            username="officer",
            password="password123",
            role=User.Role.ACCOUNT_OFFICER,
        )
        response = self.client.post(
            reverse("admin:users_user_change", args=[officer.pk]),
            self._change_payload(officer, is_staff="on"),
        )
        # Change form re-renders with a validation error (200, not 302).
        self.assertEqual(response.status_code, 200)
        officer.refresh_from_db()
        self.assertFalse(officer.is_staff)
        self.assertEqual(officer.role, User.Role.ACCOUNT_OFFICER)

    def test_legacy_staff_non_admin_save_is_rejected_and_unchanged(self):
        """An inconsistent account keeps its flags when the save is rejected."""
        officer = User.objects.create_user(
            username="officer",
            password="password123",
            role=User.Role.ACCOUNT_OFFICER,
            is_staff=True,
        )
        response = self.client.post(
            reverse("admin:users_user_change", args=[officer.pk]),
            self._change_payload(officer),
        )
        self.assertEqual(response.status_code, 200)
        officer.refresh_from_db()
        self.assertTrue(officer.is_staff)
        self.assertEqual(officer.role, User.Role.ACCOUNT_OFFICER)

    def test_assigning_system_administrator_grants_staff(self):
        """Saving a user with the admin role sets is_staff on the same save."""
        officer = User.objects.create_user(
            username="officer",
            password="password123",
            role=User.Role.ACCOUNT_OFFICER,
        )
        response = self.client.post(
            reverse("admin:users_user_change", args=[officer.pk]),
            self._change_payload(officer, role=User.Role.SYSTEM_ADMINISTRATOR),
        )
        self.assertRedirects(response, reverse("admin:users_user_changelist"))
        officer.refresh_from_db()
        self.assertEqual(officer.role, User.Role.SYSTEM_ADMINISTRATOR)
        self.assertTrue(officer.is_staff)

    def test_demoting_system_administrator_clears_staff_keeps_superuser(self):
        """Demoting an admin clears is_staff and leaves is_superuser intact."""
        admin_user = User.objects.create_superuser(
            username="otheradmin", email="", password="password123"
        )
        admin_user.role = User.Role.SYSTEM_ADMINISTRATOR
        admin_user.save(update_fields=["role"])
        response = self.client.post(
            reverse("admin:users_user_change", args=[admin_user.pk]),
            self._change_payload(admin_user, role=User.Role.MANAGER),
        )
        self.assertRedirects(response, reverse("admin:users_user_changelist"))
        admin_user.refresh_from_db()
        self.assertEqual(admin_user.role, User.Role.MANAGER)
        self.assertFalse(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
