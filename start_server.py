#!/usr/bin/env python
"""
Startup script to initialize Django database and start server
"""

import os
import sys
import django
from django.core.management import execute_from_command_line


def main():
    """Initialize database and start server"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "remedial.settings")
    django.setup()

    # First, run migrations to ensure all tables are created
    print("Running migrations...")
    execute_from_command_line(["manage.py", "migrate"])

    # Then start the server
    print("Starting Django server...")
    execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8000"])


if __name__ == "__main__":
    main()
