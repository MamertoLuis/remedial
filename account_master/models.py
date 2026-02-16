from django.db import models

class AccountMaster(models.Model):
    ACCOUNT_STATUS_CHOICES = [
        ('Performing', 'Performing'),
        ('Past Due', 'Past Due'),
        ('NPL', 'NPL'),
        ('Written-Off', 'Written-Off'),
    ]

    SECURITY_TYPE_CHOICES = [
        ('Unsecured', 'Unsecured'),
        ('REM', 'REM'),
        ('CM', 'CM'),
        ('Mixed', 'Mixed'),
    ]

    account_id = models.CharField(max_length=20, primary_key=True)
    borrower_id = models.CharField(max_length=20)
    borrower_name = models.CharField(max_length=255)
    loan_type = models.CharField(max_length=50)
    booking_date = models.DateField()
    original_principal = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    maturity_date = models.DateField()
    branch_code = models.CharField(max_length=10)
    account_officer = models.CharField(max_length=100)
    security_type = models.CharField(max_length=20, choices=SECURITY_TYPE_CHOICES)
    current_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES)
    days_past_due = models.IntegerField()
    npl_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.account_id
