from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ACCOUNT_OFFICER = "ACCOUNT_OFFICER", _("Account Officer")
        MANAGER = "MANAGER", _("Manager")
        BOARD_MEMBER = "BOARD_MEMBER", _("Board Member")

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.ACCOUNT_OFFICER
    )

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="users_user_set",  # Unique related name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="users_user_permissions_set",  # Unique related name
        related_query_name="user",
    )
