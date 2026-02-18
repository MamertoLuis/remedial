from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Role(models.TextChoices):
        ACCOUNT_OFFICER = 'ACCOUNT_OFFICER', _('Account Officer')
        MANAGER = 'MANAGER', _('Manager')
        BOARD_MEMBER = 'BOARD_MEMBER', _('Board Member')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ACCOUNT_OFFICER)
