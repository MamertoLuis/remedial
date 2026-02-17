
class ECLProvisionHistoryForm(forms.ModelForm):
    class Meta:
        model = ECLProvisionHistory
        fields = '__all__'
        widgets = {
            'as_of_date': forms.DateInput(attrs={'type': 'date'}),
        }