#!/bin/bash

echo "Removing database..."
rm -f db.sqlite3

echo "Removing migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -not -path "*/.venv/*" -delete
find . -path "*/migrations/*.pyc" -not -path "*/.venv/*" -delete

echo "Making migrations..."
uv run python manage.py makemigrations

echo "Migrating..."
uv run python manage.py migrate

echo "Creating superuser..."
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword123')
    print('Superuser created successfully.')
else:
    print('Superuser already exists.')
"

echo "Database reset complete!"
