from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from models import Profile

class SignUpForm(UserCreationForm):
    birth_date = forms.DateField(help_text='Required. Format: YYYY-MM-DD')
    location = forms.CharField(label='Location:' )	
    class Meta:
        model = User
        fields = ('username', 'birth_date', 'password1', 'password2', 'location')

class TopUpForm(ModelForm):
    USD = forms.IntegerField(label='USD:')
    EUR = forms.IntegerField(label='EUR:')
    class Meta:
        model = User
        fields = ('USD', 'EUR')

class WithdrawForm(ModelForm):
    USD = forms.IntegerField(label='USD:')
    EUR = forms.IntegerField(label='EUR:')
    class Meta:
        model = User
        fields = ('USD', 'EUR')

class TransferForm(ModelForm):
    USD = forms.IntegerField(label='USD:')
    EUR = forms.IntegerField(label='EUR:')
    username = forms.CharField(label='User:')
    class Meta:
        model = User
        fields = ('USD', 'EUR')

