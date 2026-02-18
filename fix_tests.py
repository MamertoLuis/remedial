#!/usr/bin/env python
"""
Script to fix all test data issues in API tests
"""

import os
import re


def fix_test_api_py():
    """Fix test_api.py file"""
    filepath = "/home/marty/workspace/remedial/api/tests/test_api.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Fix Borrower.objects.create calls to include email and mobile
    # 1. Fix the first Borrower creation in test_loan_filtering
    pattern1 = r'Borrower\.objects\.create\(\s*borrower_id="BOR011",\s*full_name="Filter Test",\s*mobile="09171111111"\s*\)'
    replacement1 = 'Borrower.objects.create(\n            borrower_id="BOR011", full_name="Filter Test", mobile="09171111111", email="filter@example.com"\n        )'
    content = re.sub(pattern1, replacement1, content)

    # 2. Fix the Borrower creation in test_pagination
    pattern2 = r'Borrower\.objects\.create\(\s*borrower_id="BOR012",\s*full_name="Pagination Test"\s*\)'
    replacement2 = 'Borrower.objects.create(\n            borrower_id="BOR012", full_name="Pagination Test", mobile="09172222222", email="pagination@example.com"\n        )'
    content = re.sub(pattern2, replacement2, content)

    # Fix pn_number conflicts in test_pagination
    # Change pn_number=f"PN{i:03d}" to pn_number=f"PAG{i:03d}"
    content = re.sub(r'pn_number=f"PN\{i:03d\}"', 'pn_number=f"PAG{i:03d}"', content)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")


def fix_test_serializers_py():
    """Fix test_serializers.py file"""
    filepath = "/home/marty/workspace/remedial/api/tests/test_serializers.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Fix Borrower.objects.create call to include email and mobile
    pattern = r'Borrower\.objects\.create\(borrower_id="BOR002", full_name="Jane Doe"\)'
    replacement = 'Borrower.objects.create(borrower_id="BOR002", full_name="Jane Doe", mobile="09174444444", email="jane@example.com")'
    content = re.sub(pattern, replacement, content)

    # Fix pn_number conflicts
    # Change PN001 to SER001 and PN002 to SER002
    content = content.replace('pn_number="PN001"', 'pn_number="SER001"')
    content = content.replace('pn_number="PN002"', 'pn_number="SER002"')

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")


def fix_test_views_py():
    """Fix test_views.py file"""
    filepath = "/home/marty/workspace/remedial/api/tests/test_views.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Fix all Borrower.objects.create calls to include email and mobile
    # 1. Fix in test_list_borrowers
    pattern1 = (
        r'Borrower\.objects\.create\(borrower_id="TEST_BOR001", full_name="John Doe"\)'
    )
    replacement1 = 'Borrower.objects.create(borrower_id="TEST_BOR001", full_name="John Doe", mobile="09175555555", email="john@example.com")'
    content = re.sub(pattern1, replacement1, content)

    pattern2 = (
        r'Borrower\.objects\.create\(borrower_id="TEST_BOR002", full_name="Jane Doe"\)'
    )
    replacement2 = 'Borrower.objects.create(borrower_id="TEST_BOR002", full_name="Jane Doe", mobile="09176666666", email="jane@example.com")'
    content = re.sub(pattern2, replacement2, content)

    # 3. Fix in test_retrieve_borrower
    pattern3 = r'Borrower\.objects\.create\(\s*borrower_id="BOR004",\s*full_name="Alice Brown"\s*\)'
    replacement3 = 'Borrower.objects.create(\n            borrower_id="BOR004", full_name="Alice Brown", mobile="09177777777", email="alice@example.com"\n        )'
    content = re.sub(pattern3, replacement3, content)

    # 4. Fix in setUp for LoanAccountViewSetTest
    pattern4 = r'Borrower\.objects\.create\(\s*borrower_id="BOR005",\s*full_name="Test Borrower"\s*\)'
    replacement4 = 'Borrower.objects.create(\n            borrower_id="BOR005", full_name="Test Borrower", mobile="09178888888", email="testborrower@example.com"\n        )'
    content = re.sub(pattern4, replacement4, content)

    # 5. Fix borrower_data in test_create_borrower
    pattern5 = r'("borrower_id": "TEST_BOR003",\s*"borrower_type": "PERSON",\s*"full_name": "Bob Smith",\s*"primary_address": "456 Test Ave",\s*"tin": "TIN003")'
    replacement5 = r'"borrower_id": "TEST_BOR003",\n            "borrower_type": "PERSON",\n            "full_name": "Bob Smith",\n            "primary_address": "456 Test Ave",\n            "tin": "TIN003",\n            "mobile": "09179999999",\n            "email": "bob@example.com"'
    content = re.sub(pattern5, replacement5, content)

    # Fix pn_number conflicts
    # Change all PNxxx to VIEWxxx
    content = re.sub(r'pn_number="PN(\d+)"', r'pn_number="VIEW\1"', content)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")


if __name__ == "__main__":
    fix_test_api_py()
    fix_test_serializers_py()
    fix_test_views_py()
    print("All test files fixed!")
