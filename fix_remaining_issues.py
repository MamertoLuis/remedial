#!/usr/bin/env python
"""
Script to fix remaining test data issues in API tests
"""

import re


def fix_remaining_issues():
    """Fix remaining issues in test files"""

    # Fix test_api.py
    filepath = "/home/marty/workspace/remedial/api/tests/test_api.py"

    with open(filepath, "r") as f:
        content = f.read()

    # 1. Add risk_rating to borrower_data
    pattern1 = r'("email": "test@example.com")'
    replacement1 = r'"email": "test@example.com",\n            "risk_rating": "LOW"'
    content = re.sub(pattern1, replacement1, content)

    # 2. Add risk_rating to existing Borrower.objects.create call
    pattern2 = r'Borrower\.objects\.create\(\s*borrower_id="BOR011",\s*full_name="Filter Test",\s*mobile="09171111111",\s*email="filter@example.com"\s*\)'
    replacement2 = 'Borrower.objects.create(\n            borrower_id="BOR011", full_name="Filter Test", mobile="09171111111", email="filter@example.com", risk_rating="MEDIUM"\n        )'
    content = re.sub(pattern2, replacement2, content)

    # 3. Add risk_rating to pagination Borrower.objects.create call
    pattern3 = r'Borrower\.objects\.create\(\s*borrower_id="BOR012",\s*full_name="Pagination Test"\s*\)'
    replacement3 = 'Borrower.objects.create(\n            borrower_id="BOR012", full_name="Pagination Test", mobile="09172222222", email="pagination@example.com", risk_rating="LOW"\n        )'
    content = re.sub(pattern3, replacement3, content)

    # 4. Fix URL pattern names
    content = content.replace('reverse("account-list")', 'reverse("loanaccount-list")')

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")

    # Fix test_serializers.py
    filepath = "/home/marty/workspace/remedial/api/tests/test_serializers.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Add risk_rating to borrower_data
    pattern1 = r'("mobile": "09173333333")'
    replacement1 = r'"mobile": "09173333333",\n            "risk_rating": "LOW"'
    content = re.sub(pattern1, replacement1, content)

    # Add risk_rating to Borrower.objects.create call
    pattern2 = r'Borrower\.objects\.create\(borrower_id="BOR002", full_name="Jane Doe", mobile="09174444444", email="jane@example.com"\)'
    replacement2 = 'Borrower.objects.create(borrower_id="BOR002", full_name="Jane Doe", mobile="09174444444", email="jane@example.com", risk_rating="MEDIUM")'
    content = re.sub(pattern2, replacement2, content)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")

    # Fix test_views.py
    filepath = "/home/marty/workspace/remedial/api/tests/test_views.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Add risk_rating to all Borrower.objects.create calls
    content = re.sub(
        r'Borrower\.objects\.create\(borrower_id="TEST_BOR001", full_name="John Doe", mobile="09175555555", email="john@example.com"\)',
        'Borrower.objects.create(borrower_id="TEST_BOR001", full_name="John Doe", mobile="09175555555", email="john@example.com", risk_rating="LOW")',
        content,
    )

    content = re.sub(
        r'Borrower\.objects\.create\(borrower_id="TEST_BOR002", full_name="Jane Doe", mobile="09176666666", email="jane@example.com"\)',
        'Borrower.objects.create(borrower_id="TEST_BOR002", full_name="Jane Doe", mobile="09176666666", email="jane@example.com", risk_rating="MEDIUM")',
        content,
    )

    # Add risk_rating to multi-line Borrower.objects.create calls
    content = re.sub(
        r'Borrower\.objects\.create\(\s*borrower_id="BOR004",\s*full_name="Alice Brown",\s*mobile="09177777777",\s*email="alice@example.com"\s*\)',
        'Borrower.objects.create(\n            borrower_id="BOR004", full_name="Alice Brown", mobile="09177777777", email="alice@example.com", risk_rating="LOW"\n        )',
        content,
    )

    content = re.sub(
        r'Borrower\.objects\.create\(\s*borrower_id="BOR005",\s*full_name="Test Borrower",\s*mobile="09178888888",\s*email="testborrower@example.com"\s*\)',
        'Borrower.objects.create(\n            borrower_id="BOR005", full_name="Test Borrower", mobile="09178888888", email="testborrower@example.com", risk_rating="MEDIUM"\n        )',
        content,
    )

    # Add risk_rating to borrower_data
    content = re.sub(
        r'"email": "bob@example.com"',
        '"email": "bob@example.com",\n            "risk_rating": "LOW"',
        content,
    )

    # Fix URL pattern names
    content = content.replace('reverse("account-list")', 'reverse("loanaccount-list")')
    content = content.replace(
        'reverse("account-activities")', 'reverse("loanaccount-activities")'
    )

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")


if __name__ == "__main__":
    fix_remaining_issues()
    print("All remaining issues fixed!")
