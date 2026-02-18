from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from account_master.models import Borrower, LoanAccount, RemedialStrategy
from .models import CompromiseAgreement, CompromiseInstallment
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

class CompromiseAgreementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.borrower = Borrower.objects.create(
            borrower_id=f'B001_{self._testMethodName}',
            full_name='John Doe',
            email='john.doe@example.com',
            primary_address='123 Main St'
        )
        self.loan_account = LoanAccount.objects.create(
            loan_id='LA001',
            borrower=self.borrower,
            pn_number=f'PN001_{self._testMethodName}',
            booking_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=365),
            original_principal=Decimal('100000.00'),
            interest_rate=Decimal('0.05'),
            loan_type='Personal',
            branch_code='BR001'
        )
        self.strategy = RemedialStrategy.objects.create(
            account=self.loan_account,
            strategy_type='Compromise',
            strategy_start_date=date.today(),
            strategy_status='ACTIVE'
        )
        self.compromise_agreement = CompromiseAgreement.objects.create(
            strategy=self.strategy,
            account=self.loan_account,
            original_total_exposure=Decimal('10000.00'),
            approved_compromise_amount=Decimal('5000.00'),
            approval_level='AO',
            approval_date=date.today(),
            installment_flag=False,
            rescission_clause_flag=False,
            status='ACTIVE',
            created_by=self.user,
            updated_by=self.user
        )
        self.compromise_installment = CompromiseInstallment.objects.create(
            compromise_agreement=self.compromise_agreement,
            installment_number=1,
            due_date=date.today() + timedelta(days=30),
            amount_due=Decimal('1000.00'),
            status='UNPAID'
        )

    def test_compromise_agreement_list_view(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('compromise_agreement_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'compromise_agreement/compromise_agreement_list.html')
        self.assertContains(response, "Compromise Agreements")

    def test_compromise_agreement_list_view_no_auth(self):
        response = self.client.get(reverse('compromise_agreement_list'))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_compromise_agreement_create_view(self):
        self.client.login(username='testuser', password='testpassword')
        create_url = reverse('compromise_agreement_create', kwargs={'loan_id': self.loan_account.loan_id})
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'compromise_agreement/compromise_agreement_form.html')

        initial_count = CompromiseAgreement.objects.count()
        post_data = {
            'strategy': self.strategy.pk,
            'account': self.loan_account.pk,
            'original_total_exposure': Decimal('10000.00'),
            'approved_compromise_amount': Decimal('5000.00'),
            'approval_level': 'AO',
            'approval_date': date.today(),
            'installment_flag': False,
            'rescission_clause_flag': False,
            'status': 'ACTIVE',
        }
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to account detail view
        self.assertEqual(CompromiseAgreement.objects.count(), initial_count + 1)
        new_agreement = CompromiseAgreement.objects.last()
        self.assertEqual(new_agreement.strategy, self.strategy)
        self.assertEqual(new_agreement.approved_compromise_amount, Decimal('5000.00'))

    def test_compromise_agreement_detail_view(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('compromise_agreement_detail', kwargs={'pk': self.compromise_agreement.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'compromise_agreement/compromise_agreement_detail.html')
        self.assertContains(response, str(self.compromise_agreement.compromise_id))
        self.assertContains(response, "5,000.00")

    def test_compromise_agreement_detail_view_no_auth(self):
        response = self.client.get(reverse('compromise_agreement_detail', kwargs={'pk': self.compromise_agreement.pk}))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_compromise_agreement_update_view(self):
        self.client.login(username='testuser', password='testpassword')
        update_url = reverse('compromise_agreement_update', kwargs={'pk': self.compromise_agreement.pk})
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'compromise_agreement/compromise_agreement_form.html')

        updated_amount = Decimal('6000.00')
        post_data = {
            'strategy': self.strategy.pk,
            'account': self.loan_account.pk,
            'original_total_exposure': self.compromise_agreement.original_total_exposure,
            'approved_compromise_amount': updated_amount,
            'approval_level': 'MANAGER',
            'approval_date': date.today(),
            'installment_flag': True,
            'rescission_clause_flag': False,
            'status': 'COMPLETED',
        }
        response = self.client.post(update_url, post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to account detail view
        self.compromise_agreement.refresh_from_db()
        self.assertEqual(self.compromise_agreement.approved_compromise_amount, updated_amount)
        self.assertEqual(self.compromise_agreement.status, 'COMPLETED')

    def test_compromise_agreement_update_view_no_auth(self):
        update_url = reverse('compromise_agreement_update', kwargs={'pk': self.compromise_agreement.pk})
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_compromise_installment_create_view(self):
        self.client.login(username='testuser', password='testpassword')
        create_url = reverse('compromise_installment_create', kwargs={'agreement_pk': self.compromise_agreement.pk})
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'compromise_agreement/compromise_installment_form.html')

        initial_count = CompromiseInstallment.objects.count()
        post_data = {
            'compromise_agreement': self.compromise_agreement.pk,
            'installment_number': 1,
            'due_date': date.today() + timedelta(days=30),
            'amount_due': Decimal('1000.00'),
            'amount_paid': Decimal('0.00'),
            'payment_date': '',  # Can be empty
            'status': 'UNPAID',
        }
        response = self.client.post(create_url, post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to detail view
        self.assertEqual(CompromiseInstallment.objects.count(), initial_count + 1)
        new_installment = CompromiseInstallment.objects.last()
        self.assertEqual(new_installment.compromise_agreement, self.compromise_agreement)
        self.assertEqual(new_installment.installment_number, 1)
        self.assertEqual(new_installment.amount_due, Decimal('1000.00'))

    def test_compromise_installment_create_view_no_auth(self):
        create_url = reverse('compromise_installment_create', kwargs={'agreement_pk': self.compromise_agreement.pk})
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_compromise_installment_update_view(self):
        self.client.login(username='testuser', password='testpassword')
        update_url = reverse('compromise_installment_update', kwargs={'pk': self.compromise_installment.pk})
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'compromise_agreement/compromise_installment_form.html')

        updated_amount_paid = Decimal('500.00')
        post_data = {
            'compromise_agreement': self.compromise_agreement.pk,
            'installment_number': 1,
            'due_date': date.today() + timedelta(days=30),
            'amount_due': Decimal('1000.00'),
            'amount_paid': updated_amount_paid,
            'payment_date': date.today(),
            'status': 'PAID',
        }
        response = self.client.post(update_url, post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to detail view
        self.compromise_installment.refresh_from_db()
        self.assertEqual(self.compromise_installment.amount_paid, updated_amount_paid)
        self.assertEqual(self.compromise_installment.status, 'PAID')

    def test_compromise_installment_update_view_no_auth(self):
        update_url = reverse('compromise_installment_update', kwargs={'pk': self.compromise_installment.pk})
        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 302) # Redirect to login
