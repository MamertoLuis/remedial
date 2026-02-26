import re

with open('account_master/models.py', 'r') as f:
    content = f.read()

borrower_replacement = """    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('borrower_detail', args=[str(self.borrower_id)])"""

content = content.replace("""    def __str__(self):
        return self.full_name""", borrower_replacement)

loan_replacement = """    def __str__(self):
        return self.loan_id

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('account_detail', args=[str(self.loan_id)])"""

content = content.replace("""    def __str__(self):
        return self.loan_id""", loan_replacement)

with open('account_master/models.py', 'w') as f:
    f.write(content)
