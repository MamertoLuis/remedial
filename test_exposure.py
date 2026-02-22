import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "remedial.settings")
django.setup()

from account_master.models import Exposure
from django.db.models import Max, Subquery, Sum

print("Query 1:")
q1 = Exposure.objects.filter(as_of_date__isnull=False).values("account_id").annotate(latest_date=Max("as_of_date")).values("exposure_id")
print(q1.query)

print("\nQuery 2:")
from django.db.models import OuterRef
latest_exposures = Exposure.objects.filter(
    account=OuterRef('account')
).order_by('-as_of_date')

q2 = Exposure.objects.filter(
    pk=Subquery(latest_exposures.values('pk')[:1])
)
print(q2.query)
print(q2.aggregate(total=Sum('principal_outstanding')))

