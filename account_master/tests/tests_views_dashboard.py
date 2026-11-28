from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch
from account_master.models import Borrower, LoanAccount

User = get_user_model()

class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.dashboard_url = reverse('dashboard')
        self.search_url = reverse('search')

    def test_dashboard_requires_login(self):
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [302, 403])

    @patch('account_master.services.dashboard_service.DashboardService.get_portfolio_kpis')
    @patch('account_master.services.activity_service.ActivityService.get_recent_activities')
    @patch('account_master.services.alert_service.AlertService.get_alert_counts')
    @patch('account_master.services.alert_service.AlertService.get_active_alerts')
    def test_dashboard_authenticated(self, mock_active_alerts, mock_alert_counts, mock_recent_activities, mock_kpis):
        mock_kpis.return_value = {'total_loans': 10}
        mock_recent_activities.return_value = []
        mock_alert_counts.return_value = {'total': 5}
        mock_active_alerts.return_value = []

        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account_master/dashboard.html')
        self.assertIn('kpis', response.context)
        self.assertIn('activities', response.context)
        self.assertIn('alert_counts', response.context)
        self.assertIn('active_alerts', response.context)
        self.assertEqual(response.context['kpis'], {'total_loans': 10})

class SearchViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.search_url = reverse('search')
        
        self.borrower = Borrower.objects.create(
            borrower_id='B001',
            full_name='John Doe',
            primary_address='123 Main St',
            mobile='1234567890'
        )
        self.loan = LoanAccount.objects.create(
            loan_id='L001',
            borrower=self.borrower,
            original_principal=1000,
            interest_rate=5.0,
            status='PERFORMING',
            booking_date=timezone.now().date(),
            maturity_date=timezone.now().date() + timezone.timedelta(days=365)
        )

    def test_search_requires_login(self):
        response = self.client.get(self.search_url)
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [302, 403])

    def test_search_authenticated_no_query(self):
        self.client.force_login(self.user)
        response = self.client.get(self.search_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search/search_results.html')
        self.assertEqual(response.context['query'], '')
        self.assertEqual(response.context['search_results'], [])
        self.assertEqual(response.context['total_results'], 0)

    def test_search_authenticated_with_query_borrower(self):
        self.client.force_login(self.user)
        response = self.client.get(self.search_url, {'q': 'John'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search/search_results.html')
        self.assertEqual(response.context['query'], 'John')
        self.assertTrue(len(response.context['search_results']) > 0)
        
        # Check if borrower is in results
        borrower_found = any(res['type'] == 'borrower' and 'John' in res['title'] for res in response.context['search_results'])
        self.assertTrue(borrower_found)

    def test_search_authenticated_with_query_loan(self):
        self.client.force_login(self.user)
        response = self.client.get(self.search_url, {'q': 'L001'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search/search_results.html')
        self.assertEqual(response.context['query'], 'L001')
        self.assertTrue(len(response.context['search_results']) > 0)
        
        # Check if loan is in results
        loan_found = any(res['type'] == 'loan' and 'L001' in res['title'] for res in response.context['search_results'])
        self.assertTrue(loan_found)
