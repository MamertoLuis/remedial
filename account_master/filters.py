import django_filters
from .models import Borrower

class BorrowerFilter(django_filters.FilterSet):
    full_name = django_filters.CharFilter(lookup_expr='icontains', label='Borrower Name')

    class Meta:
        model = Borrower
        fields = ['full_name']
