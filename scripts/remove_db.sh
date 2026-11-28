#!/bin/bash

echo "Removing database..."
rm -f db.sqlite3

echo "Removing migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -not -path "*/.venv/*" -delete
find . -path "*/migrations/*.pyc" -not -path "*/.venv/*" -delete


