from django.test import TestCase
from django.contrib.auth import get_user_model

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
