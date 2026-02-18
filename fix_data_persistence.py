#!/usr/bin/env python
"""
Script to fix data persistence issues in API tests
"""

import re


def fix_data_persistence():
    """Fix data persistence issues in test files"""

    # Fix test_api.py
    filepath = "/home/marty/workspace/remedial/api/tests/test_api.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Add cleanup to test_loan_filtering
    pattern1 = r'def test_loan_filtering\(self\):(\s*)"""Test that loan accounts can be filtered by various criteria"""(\s*)# Create test data'
    replacement1 = r'def test_loan_filtering(self):\1        """Test that loan accounts can be filtered by various criteria"""\2        # Clean up any existing test data\2        Borrower.objects.filter(borrower_id__startswith="TEST_FIL").delete()\2        LoanAccount.objects.filter(loan_id__startswith="LN01").delete()\2\2        # Create test data'
    content = re.sub(pattern1, replacement1, content)

    # Add cleanup to test_pagination
    pattern2 = r'def test_pagination\(self\):(\s*)"""Test that API responses are properly paginated"""\2# Create 25 loans to test pagination'
    replacement2 = r'def test_pagination(self):\1        """Test that API responses are properly paginated"""\2        # Clean up any existing test data\2        Borrower.objects.filter(borrower_id__startswith="TEST_PAG").delete()\2        LoanAccount.objects.filter(loan_id__startswith="PAG").delete()\2\2        # Create 25 loans to test pagination'
    content = re.sub(pattern2, replacement2, content)

    # Update test_loan_filtering to expect correct count and clean up properly
    content = re.sub(
        r"self\.assertEqual\(len\(performing_loans\), 2\)",
        "self.assertEqual(len(performing_loans), 2)  # Only our test loans",
        content,
    )

    # Update test_pagination to expect correct count
    content = re.sub(
        r'self\.assertEqual\(response\.data\["count"\], 25\)',
        'self.assertEqual(response.data["count"], 25)  # Only our test loans',
        content,
    )

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")

    # Fix test_views.py to add proper cleanup
    filepath = "/home/marty/workspace/remedial/api/tests/test_views.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Add more comprehensive cleanup to test_list_borrowers
    pattern = r'# Clear existing borrowers to get accurate count(\s*)Borrower\.objects\.filter\(borrower_id__startswith="TEST_\)\.delete\(\)'
    replacement = r'# Clear existing test data to get accurate count\1Borrower.objects.filter(borrower_id__startswith="TEST_").delete()\1LoanAccount.objects.filter(loan_id__startswith="LN00").delete()'
    content = re.sub(pattern, replacement, content)

    # Add cleanup to LoanAccountViewSetTest setUp
    pattern2 = r'class LoanAccountViewSetTest\(APITestCase\):(\s*)def setUp\(self\):(\s*)self\.user = User\.objects\.create_user\(username="testuser", password="testpass"\)(\s*)self\.client\.force_authenticate\(user=self\.user\)(\s*)self\.borrower = Borrower\.objects\.create\('
    replacement2 = r'class LoanAccountViewSetTest(APITestCase):\1\2    def setUp(self):\2        self.user = User.objects.create_user(username="testuser", password="testpass")\2        self.client.force_authenticate(user=self.user)\2        \2        # Clean up any existing test data\2        Borrower.objects.filter(borrower_id__startswith="TEST_LOAN").delete()\2        LoanAccount.objects.filter(loan_id__startswith="LN0").delete()\2\2        self.borrower = Borrower.objects.create('
    content = re.sub(pattern2, replacement2, content)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed {filepath}")


if __name__ == "__main__":
    fix_data_persistence()
    print("Data persistence issues fixed!")
