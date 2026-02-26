import re

with open('account_master/views/dashboard.py', 'r') as f:
    content = f.read()

if 'from django.contrib.auth.decorators import login_required' not in content:
    content = 'from django.contrib.auth.decorators import login_required\n' + content

content = content.replace('def dashboard(request):', '@login_required\ndef dashboard(request):')

with open('account_master/views/dashboard.py', 'w') as f:
    f.write(content)
