from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.models import User


def system_admin_required(view_func):
    """Gate a view to users with the SYSTEM_ADMINISTRATOR role.

    Composes ``@login_required`` (anonymous users are redirected to login)
    with a strict role check: any authenticated user whose ``role`` is not
    ``User.Role.SYSTEM_ADMINISTRATOR`` receives the shared 403 page.
    """

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.SYSTEM_ADMINISTRATOR:
            return render(
                request,
                "account_master/403.html",
                {"required_roles": "the SYSTEM_ADMINISTRATOR"},
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped
