from django.contrib import admin
from .models import LoanAccount, Borrower, CollectionActivityLog, RemedialStrategy, Exposure, DelinquencyStatus, ECLProvisionHistory
from .services import upsert_exposure, upsert_delinquency_status
from .services.provision_service import create_provision_entry

@admin.register(Exposure)
class ExposureAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        exposure_data = {
            'principal_outstanding': obj.principal_outstanding,
            'accrued_interest': obj.accrued_interest,
            'accrued_penalty': obj.accrued_penalty,
            'legal_fees': obj.legal_fees,
            'other_charges': obj.other_charges,
            'provision_rate': obj.provision_rate,
            'snapshot_type': obj.snapshot_type,
        }
        upsert_exposure(
            account=obj.account,
            as_of_date=obj.as_of_date,
            defaults=exposure_data
        )

@admin.register(DelinquencyStatus)
class DelinquencyStatusAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        delinquency_data = {
            'days_past_due': obj.days_past_due,
            'aging_bucket': obj.aging_bucket,
            'classification': obj.classification,
            'npl_flag': obj.npl_flag,
            'npl_date': obj.npl_date,
            'snapshot_type': obj.snapshot_type,
        }
        upsert_delinquency_status(
            account=obj.account,
            as_of_date=obj.as_of_date,
            defaults=delinquency_data
        )

@admin.register(ECLProvisionHistory)
class ECLProvisionHistoryAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        create_provision_entry(
            exposure=obj.exposure,
            provision_rate=obj.provision_rate,
            method=obj.method,
            remarks=obj.remarks,
            classification=obj.classification,
            days_past_due=obj.days_past_due,
            created_by=request.user,
        )


admin.site.register(LoanAccount)
admin.site.register(Borrower)
admin.site.register(CollectionActivityLog)
admin.site.register(RemedialStrategy)
