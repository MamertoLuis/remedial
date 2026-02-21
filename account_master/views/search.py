from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from ..models import Borrower, LoanAccount


class SearchView(LoginRequiredMixin, TemplateView):
    template_name = "search/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        if query:
            # Search borrowers
            borrowers = Borrower.objects.filter(
                Q(full_name__icontains=query)
                | Q(borrower_id__icontains=query)
                | Q(mobile__icontains=query)
            ).order_by("full_name")[:10]

            # Search loan accounts
            loans = (
                LoanAccount.objects.filter(
                    Q(loan_id__icontains=query)
                    | Q(borrower__full_name__icontains=query)
                    | Q(borrower__borrower_id__icontains=query)
                )
                .select_related("borrower")
                .order_by("loan_id")[:10]
            )

            # Prepare search results
            context["search_results"] = []

            # Add borrower results
            for borrower in borrowers:
                context["search_results"].append(
                    {
                        "type": "borrower",
                        "title": borrower.full_name,
                        "subtitle": f"Borrower ID: {borrower.borrower_id}",
                        "url": borrower.get_absolute_url(),
                        "match_text": self._highlight_match(borrower.full_name, query),
                    }
                )

            # Add loan results
            for loan in loans:
                context["search_results"].append(
                    {
                        "type": "loan",
                        "title": f"Loan: {loan.loan_id}",
                        "subtitle": f"Borrower: {loan.borrower.full_name}",
                        "url": loan.get_absolute_url(),
                        "match_text": self._highlight_match(loan.loan_id, query),
                    }
                )

            context["query"] = query
            context["total_results"] = len(context["search_results"])
        else:
            context["search_results"] = []
            context["query"] = ""
            context["total_results"] = 0

        return context

    def _highlight_match(self, text, query):
        """Simple highlighting for matching text"""
        if not query:
            return text

        query_lower = query.lower()
        text_lower = text.lower()
        start = text_lower.find(query_lower)

        if start >= 0:
            end = start + len(query)
            return f"{text[:start]}<strong>{text[start:end]}</strong>{text[end:]}"

        return text


# Create a function-based view for backward compatibility
def search(request):
    view = SearchView.as_view()
    return view(request)
