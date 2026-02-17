from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
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
        return context

class CompromiseAgreementCreateView(LoginRequiredMixin, CreateView):
    model = CompromiseAgreement
    form_class = CompromiseAgreementForm
    template_name = 'compromise_agreement/compromise_agreement_form.html'
    success_url = reverse_lazy('compromise_agreement_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

class CompromiseAgreementUpdateView(LoginRequiredMixin, UpdateView):
    model = CompromiseAgreement
    form_class = CompromiseAgreementForm
    template_name = 'compromise_agreement/compromise_agreement_form.html'
    success_url = reverse_lazy('compromise_agreement_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

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