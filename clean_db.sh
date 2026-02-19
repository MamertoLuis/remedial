#!/bin/bash

echo "Deleting SQLite database and all migrations..."

# Remove the SQLite database file
if [ -f "db.sqlite3" ]; then
    echo "Removing db.sqlite3..."
    rm -f db.sqlite3
else
    echo "db.sqlite3 not found"
fi

# Remove all migration files from all apps
echo "Removing migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Remove __pycache__ directories
echo "Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Database and migrations have been cleaned up."
echo ""
echo "Next steps:"
echo "1. Run: python manage.py makemigrations"
echo "2. Run: python manage.py migrate"
echo "3. Run: python manage.py createsuperuser"
echo "4. Run: python manage.py runserver"