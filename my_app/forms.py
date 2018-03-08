from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from models import Profile, Order

# used for the currency selection widget
currencies = [('EUR','EUR'),('USD','USD'),('RON','RON'),]
class ExchangeForm(ModelForm):
    home_currency = forms.CharField(label='From: ', widget=forms.Select(choices=currencies))
    target_currency = forms.CharField(label='To: ', widget=forms.Select(choices=currencies))
    home_currency_amount = forms.DecimalField(label='Amount: ')
    class Meta:
        model = Order
        fields = ('home_currency', 'target_currency', 'home_currency_amount')

class SignUpForm(UserCreationForm):
    birth_date = forms.DateField(help_text='Required. Format: YYYY-MM-DD')
    location = forms.CharField(label='Location:' )	
    class Meta:
        model = User
        fields = ('username', 'birth_date', 'password1', 'password2', 'location')

class TopUpForm(ModelForm):
    USD = forms.DecimalField(label='USD:')
    EUR = forms.DecimalField(label='EUR:')
    RON = forms.DecimalField(label='RON:')
    class Meta:
        model = User
        fields = ('USD', 'EUR', 'RON')

class WithdrawForm(ModelForm):
    USD = forms.DecimalField(label='USD:')
    EUR = forms.DecimalField(label='EUR:')
    RON = forms.DecimalField(label='RON:')
    class Meta:
        model = User
        fields = ('USD', 'EUR', 'RON')

class TransferForm(ModelForm):
    USD = forms.DecimalField(label='USD:')
    EUR = forms.DecimalField(label='EUR:')
    RON = forms.DecimalField(label='RON:')
    username = forms.CharField(label='User:')
    class Meta:
        model = User
        fields = ('USD', 'EUR', 'RON')

