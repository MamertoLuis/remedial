from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse
from account_master.models import Borrower, LoanAccount
from ..serializers import BorrowerSerializer

User = get_user_model()


class BorrowerSerializerTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

    def test_borrower_serializer_fields(self):
        """Test that BorrowerSerializer includes correct fields"""
        borrower_data = {
            "borrower_id": "BOR001",
            "borrower_type": "PERSON",
            "full_name": "John Doe",
            "primary_address": "123 Test St",
            "mobile": "09173333333",
            "risk_rating": "LOW",
        }
        serializer = BorrowerSerializer(data=borrower_data)
        self.assertTrue(serializer.is_valid())

    def test_borrower_serializer_loans_count(self):
        """Test that loans_count is calculated correctly"""
        borrower = Borrower.objects.create(borrower_id="BOR002", full_name="Jane Doe", mobile="09174444444", email="jane@example.com", risk_rating="MEDIUM")
        LoanAccount.objects.create(
            loan_id="LN001",
            borrower=borrower,
            original_principal=10000,
            interest_rate=5.5,
            loan_type="Personal",
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="SER001",
        )
        LoanAccount.objects.create(
            loan_id="LN002",
            borrower=borrower,
            original_principal=20000,
            interest_rate=6.0,
            loan_type="Business",
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="SER002",
        )

        serializer = BorrowerSerializer(borrower)
        self.assertEqual(serializer.data["loans_count"], 2)
