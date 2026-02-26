import re

with open('account_master/urls.py', 'r') as f:
    content = f.read()

content = content.replace("""    path(
        "account/<str:loan_id>/exposure/create/",
        views.create_exposure,
    path("account/<str:loan_id>/exposure/", views.exposure_list, name="exposure_list"),
        name="create_exposure",
    ),""", """    path(
        "account/<str:loan_id>/exposure/create/",
        views.create_exposure,
        name="create_exposure",
    ),
    path("account/<str:loan_id>/exposure/", views.exposure_list, name="exposure_list"),""")

with open('account_master/urls.py', 'w') as f:
    f.write(content)
