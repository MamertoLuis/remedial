from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User


class UserUpdateForm(UserChangeForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide password field from the form
        self.fields.pop("password", None)
