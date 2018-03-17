from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from models import Profile, Order

import datetime

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

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = ''
        self.fields['password2'].help_text = ''
        self.fields['password1'].help_text = 'At least 8 characters'

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')


class TopUpForm(forms.Form):
    currency = forms.CharField(label='Currency: ', widget=forms.Select(choices=currencies))
    amount = forms.DecimalField(label='Amount: ')

class WithdrawForm(forms.Form):
    currency = forms.CharField(label='Currency: ', widget=forms.Select(choices=currencies))
    amount = forms.DecimalField(label='Amount: ')

class TransferForm(forms.Form):
    currency = forms.CharField(label='Currency: ', widget=forms.Select(choices=currencies))
    amount = forms.DecimalField(label='Amount: ')
    username = forms.CharField(label='User:')

class ImageUploadForm(forms.Form):
    image = forms.ImageField()

def last_years():
    first_year = datetime.datetime.now().year - 6
    return list(range(first_year + 7, first_year, -1))

class AddCardForm(forms.Form):
    number = forms.CharField(label='Card Number: ', widget=forms.TextInput(attrs={'placeholder': '4111-1111-1111-1111'}))
    csv = forms.CharField(label='CSV', widget=forms.TextInput(attrs={'placeholder': '123'}))
    exp_date = forms.CharField(label='Expiration Date:', widget=forms.TextInput(attrs={'placeholder': '01/20'}))
    c_currency = forms.CharField(label='Currency:', widget=forms.Select(choices=currencies))
    name = forms.CharField(label='Name:', widget=forms.TextInput(attrs={'placeholder': 'Captain Awesome'}))
    address = forms.CharField(label='Address:', widget=forms.TextInput(attrs={'placeholder': '123 Awesome Street'}))
    phone = forms.CharField(label='Phone:', widget=forms.TextInput(attrs={'placeholder': '+44 123456789'}))
