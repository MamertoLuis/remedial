from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse
from account_master.models import Borrower, LoanAccount

User = get_user_model()


class APIIntegrationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

    def test_borrower_to_loan_relationship(self):
        """Test that borrowers and their related loans are properly linked"""
        # Create borrower
        borrower_data = {
            "borrower_id": "BOR010",
            "borrower_type": "PERSON",
            "full_name": "Integration Test Borrower",
            "primary_address": "789 Integration St",
            "tin": "TIN010",
            "mobile": "09171234567",
            "email": "test@example.com",
            "risk_rating": "LOW",
        }

        borrower_url = reverse("borrower-list")
        response = self.client.post(borrower_url, borrower_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create loan for the borrower
        borrower = Borrower.objects.get(borrower_id="BOR010")
        loan_data = {
            "loan_id": "LN010",
            "borrower": borrower.borrower_id,
            "loan_type": "Personal",
            "original_principal": 50000,
            "interest_rate": 5.5,
            "booking_date": "2023-01-01",
            "maturity_date": "2024-01-01",
            "branch_code": "001",
            "pn_number": "TEST_PN010",
        }

        loan_url = reverse("loanaccount-list")
        response = self.client.post(loan_url, loan_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify relationship
        borrower_detail_url = reverse("borrower-detail", kwargs={"pk": "BOR010"})
        response = self.client.get(borrower_detail_url)
        self.assertEqual(response.data["loans_count"], 1)

    def test_loan_filtering(self):
        """Test that loan accounts can be filtered by various criteria"""
        # Create test data
        borrower = Borrower.objects.create(
            borrower_id="BOR011",
            full_name="Filter Test",
            mobile="09171111111",
            email="filter@example.com",
            risk_rating="MEDIUM",
        )

        LoanAccount.objects.create(
            loan_id="LN011",
            borrower=borrower,
            status="PERFORMING",
            loan_type="Personal",
            original_principal=50000,
            interest_rate=5.5,
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="PN011",
        )
        LoanAccount.objects.create(
            loan_id="LN012",
            borrower=borrower,
            status="PAST_DUE",
            loan_type="Business",
            original_principal=75000,
            interest_rate=6.0,
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="PN012",
        )
        LoanAccount.objects.create(
            loan_id="LN013",
            borrower=borrower,
            status="PERFORMING",
            loan_type="Personal",
            original_principal=60000,
            interest_rate=5.5,
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            branch_code="001",
            pn_number="PN013",
        )

        # Test filtering by status
        url = reverse("loanaccount-list")
        response = self.client.get(url, {"status": "PERFORMING"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        performing_loans = [
            loan for loan in response.data["results"] if loan["status"] == "PERFORMING"
        ]
        self.assertEqual(len(performing_loans), 2)

        # Test filtering by loan type
        response = self.client.get(url, {"loan_type": "Personal"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        personal_loans = [
            loan for loan in response.data["results"] if loan["loan_type"] == "Personal"
        ]
        self.assertEqual(len(personal_loans), 2)

    def test_pagination(self):
        """Test that API responses are properly paginated"""
        # Create 25 loans to test pagination
        borrower = Borrower.objects.create(
            borrower_id="BOR012",
            full_name="Pagination Test",
            mobile="09172222222",
            email="pagination@example.com",
        )

        for i in range(25):
            loan_type = "Personal" if i % 2 == 0 else "Business"
            LoanAccount.objects.create(
                loan_id=f"LN{i:03d}",
                borrower=borrower,
                original_principal=1000 * (i + 1),
                interest_rate=5.5 if i % 2 == 0 else 6.0,
                loan_type=loan_type,
                booking_date="2023-01-01",
                maturity_date="2024-01-01",
                branch_code="001",
                pn_number=f"PAG{i:03d}",
            )

        url = reverse("loanaccount-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)  # Default page size

        # Test second page
        if response.data["next"]:
            response = self.client.get(response.data["next"])
            self.assertEqual(len(response.data["results"]), 5)
