from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from account_master.models import LoanAccount, RemedialStrategy
from .models import CompromiseAgreement, CompromiseInstallment
from .forms import CompromiseAgreementForm, CompromiseInstallmentForm
from .tables import CompromiseAgreementTable, CompromiseInstallmentTable

class CompromiseAgreementListView(LoginRequiredMixin, ListView):
    model = CompromiseAgreement
    template_name = 'compromise_agreement/compromise_agreement_list.html'
    context_object_name = 'table'

    def get_queryset(self):
        return CompromiseAgreementTable(CompromiseAgreement.objects.all())

class CompromiseAgreementDetailView(LoginRequiredMixin, DetailView):
    model = CompromiseAgreement
    template_name = 'compromise_agreement/compromise_agreement_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['installments_table'] = CompromiseInstallmentTable(
            self.object.installments.all()
        )
        context['strategy'] = self.object.strategy
        context['account'] = self.object.account
        return context

class CompromiseAgreementCreateView(LoginRequiredMixin, CreateView):
    model = CompromiseAgreement
    form_class = CompromiseAgreementForm
    template_name = 'compromise_agreement/compromise_agreement_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.strategy = get_object_or_404(RemedialStrategy, strategy_id=self.kwargs['strategy_id'])
        if self.strategy.strategy_status != 'ACTIVE' or self.strategy.strategy_type not in ['Compromise', 'Legal Action']:
            messages.error(request, "A compromise agreement can only be created for an active 'Compromise' or 'Legal Action' strategy.")
            return redirect('remedial_strategy_detail', loan_id=self.strategy.account.loan_id, strategy_id=self.strategy.strategy_id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop('account', None)  # Remove account from kwargs if it exists
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['strategy'] = self.strategy
        initial['account'] = self.strategy.account
        latest_exposure = self.strategy.account.exposures.order_by('-as_of_date').first()
        if latest_exposure:
            initial['original_total_exposure'] = latest_exposure.total_exposure
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.account = self.strategy.account
        form.instance.strategy = self.strategy
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('remedial_strategy_detail', kwargs={'loan_id': self.object.account.loan_id, 'strategy_id': self.object.strategy.strategy_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.strategy
        context['account'] = self.strategy.account
        return context

class CompromiseAgreementUpdateView(LoginRequiredMixin, UpdateView):
    model = CompromiseAgreement
    form_class = CompromiseAgreementForm
    template_name = 'compromise_agreement/compromise_agreement_form.html'

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('remedial_strategy_detail', kwargs={'loan_id': self.object.account.loan_id, 'strategy_id': self.object.strategy.strategy_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['strategy'] = self.object.strategy
        context['account'] = self.object.account
        return context

class CompromiseInstallmentCreateView(LoginRequiredMixin, CreateView):
    model = CompromiseInstallment
    form_class = CompromiseInstallmentForm
    template_name = 'compromise_agreement/compromise_installment_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['compromise_agreement'] = self.kwargs.get('agreement_pk')
        return initial

    def get_success_url(self):
        return reverse('compromise_agreement_detail', kwargs={'pk': self.kwargs.get('agreement_pk')})

class CompromiseInstallmentUpdateView(LoginRequiredMixin, UpdateView):
    model = CompromiseInstallment
    form_class = CompromiseInstallmentForm
    template_name = 'compromise_agreement/compromise_installment_form.html'

    def get_success_url(self):
        return reverse('compromise_agreement_detail', kwargs={'pk': self.object.compromise_agreement.pk})
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO

@login_required
def generate_term_sheet_pdf(request, pk):
    agreement = get_object_or_404(CompromiseAgreement, pk=pk)
    installments = agreement.installments.all().order_by('installment_number')

    context = {
        'agreement': agreement,
        'installments': installments,
        'request': request,
    }
    template = get_template('compromise_agreement/term_sheet_pdf.html')
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=Compromise_Agreement_{agreement.compromise_id}_Term_Sheet.pdf'
        return response
    return HttpResponse('We had some errors <pre>%s</pre>' % html)

