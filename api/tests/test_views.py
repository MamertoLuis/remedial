from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse
from account_master.models import Borrower, LoanAccount

User = get_user_model()


class BorrowerViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

    def test_list_borrowers(self):
        """Test GET /api/v1/borrowers/ returns list of borrowers"""
        # Clear existing borrowers to get accurate count
        Borrower.objects.filter(borrower_id__startswith="TEST_").delete()
        Borrower.objects.create(
            borrower_id="TEST_BOR001",
            full_name="John Doe",
            mobile="09175555555",
            email="john@example.com",
            risk_rating="LOW",
        )
        Borrower.objects.create(
            borrower_id="TEST_BOR002",
            full_name="Jane Doe",
            mobile="09176666666",
            email="jane@example.com",
            risk_rating="MEDIUM",
        )

        url = reverse("borrower-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that we have at least our test borrowers
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_create_borrower(self):
        """Test POST /api/v1/borrowers/ creates a new borrower"""
        data = {
            "borrower_id": "TEST_BOR003",
            "borrower_type": "PERSON",
            "full_name": "Bob Smith",
            "primary_address": "456 Test Ave",
            "tin": "TIN003",
            "mobile": "09179999999",
            "email": "bob@example.com",
            "risk_rating": "LOW",
        }

        url = reverse("borrower-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Borrower.objects.filter(borrower_id="TEST_BOR003").exists())

    def test_retrieve_borrower(self):
        """Test GET /api/v1/borrowers/{id}/ returns specific borrower"""
        borrower = Borrower.objects.create(
            borrower_id="BOR004",
            full_name="Alice Brown",
            mobile="09177777777",
            email="alice@example.com",
            risk_rating="LOW",
        )

        url = reverse("borrower-detail", kwargs={"pk": borrower.borrower_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["borrower_id"], "BOR004")
        self.assertEqual(response.data["full_name"], "Alice Brown")


class LoanAccountViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)
        self.borrower = Borrower.objects.create(
            borrower_id="BOR005",
            full_name="Test Borrower",
            mobile="09178888888",
            email="testborrower@example.com",
            risk_rating="MEDIUM",
        )

    def test_list_loan_accounts(self):
        """Test GET /api/v1/accounts/ returns list of loan accounts"""
        LoanAccount.objects.create(
            loan_id="LN003",
            borrower=self.borrower,
            original_principal=15000,
            interest_rate=5.5,
            loan_type="Personal",
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="VIEW003",
        )
        LoanAccount.objects.create(
            loan_id="LN004",
            borrower=self.borrower,
            original_principal=25000,
            interest_rate=6.0,
            loan_type="Business",
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="VIEW004",
        )

        url = reverse("loanaccount-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_get_loan_account_exposures(self):
        """Test GET /api/v1/accounts/{id}/exposures/ returns exposures"""
        loan = LoanAccount.objects.create(
            loan_id="LN005",
            borrower=self.borrower,
            original_principal=30000,
            interest_rate=5.5,
            loan_type="Personal",
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="VIEW005",
        )

        url = reverse("loanaccount-exposures", kwargs={"pk": loan.loan_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_loan_account_activities(self):
        """Test GET /api/v1/accounts/{id}/activities/ returns activities"""
        loan = LoanAccount.objects.create(
            loan_id="LN006",
            borrower=self.borrower,
            original_principal=40000,
            interest_rate=6.0,
            loan_type="Business",
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="VIEW006",
        )

        url = reverse("loanaccount-activities", kwargs={"pk": loan.loan_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
