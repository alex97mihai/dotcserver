# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import decimal
import datetime
from django.shortcuts import render

from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from my_app.forms import SignUpForm, TopUpForm, WithdrawForm, TransferForm, ExchangeForm
from models import Profile as DjProfile
from models import Order
from django.contrib.auth.models import User as dbUser
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# Non-django imports
from lib import converter
from .tasks import test_celery
# Create your views here.

from django.views.generic import TemplateView

class HomeView(TemplateView):
	template_name = 'index.html'

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()  # load the profile instance created by the signal
            user.profile.birth_date = form.cleaned_data.get('birth_date')
            user.save()
            user.profile.location = form.cleaned_data.get('location')
	    user.save()
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect('/hello/')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def topup(request):
    user = request.user
    if request.method == 'POST':
        form = TopUpForm(request.POST)
        if form.is_valid():
            if (form.cleaned_data.get('USD') > 0):
                user.profile.USD = user.profile.USD + form.cleaned_data.get('USD')
                user.save()
            if (form.cleaned_data.get('EUR') > 0):
                user.profile.EUR = user.profile.EUR + form.cleaned_data.get('EUR')
                user.save()
            return redirect('/hello/')
    else:
        form = TopUpForm()
    return render(request, 'topup.html', {'form': form})

def withdraw(request):
    user = request.user
    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            if (form.cleaned_data.get('USD') > 0):
                user.profile.USD = user.profile.USD - form.cleaned_data.get('USD')
                user.save()
            if (form.cleaned_data.get('EUR') > 0):
                user.profile.EUR = user.profile.EUR - form.cleaned_data.get('EUR')
                user.save()
            return redirect('/hello/')
    else:
        form = WithdrawForm()
    return render(request, 'withdraw.html', {'form': form})

@login_required
def transfer(request):
    user = request.user
    if request.method == 'POST':
        form = TransferForm(request.POST)
	#out2 = open(os.path.join('/home/ubuntu/myproject/my_app/out', 'out.txt'), 'w')
        #out2.write('ahaha')
        #out2.close()
        if form.is_valid():
            # get user by username
            uid = dbUser.objects.get(username=form.cleaned_data.get('username'))
            
            EURtr = form.cleaned_data.get('EUR')
            USDtr = form.cleaned_data.get('USD')
            
	    # if user has enough EUR to transfer
            if user.profile.EUR >= EURtr:
                uid.profile.EUR = uid.profile.EUR + EURtr
                user.profile.EUR = user.profile.EUR - EURtr

            if user.profile.USD >= USDtr:
                uid.profile.USD = uid.profile.USD + USDtr
                user.profile.USD = user.profile.USD - USDtr
            user.save()
            uid.save()
            out = open(os.path.join('/home/ubuntu/myproject/my_app/out', 'out.txt'), 'w')
            out.write(str(uid.profile.EUR))
            out.write('\n')
            out.write(str(uid.profile.USD))
            out.close()
        return redirect('/hello/')
    else:
        form = TransferForm()
    return render(request, 'transfer.html', {'form': form})

def viewRates(request):
    c = converter.CurrencyRates()
    eurrate  = c.get_rate('EUR', 'USD')
    usdrate  = c.get_rate('USD', 'EUR')
    context_dict = {'eurrate': eurrate, 'usdrate': usdrate}
    return render(request, 'rates.html', context_dict)

def exchange(request):
    if request.method == 'POST':
        error = False
        user = request.user
        c = converter.CurrencyRates()
        form = ExchangeForm(request.POST)
        if form.is_valid():
            home_currency = form.cleaned_data.get('home_currency')
            target_currency = form.cleaned_data.get('target_currency')
            home_currency_amount = decimal.Decimal(form.cleaned_data.get('home_currency_amount'))
            username = user.username
            date = datetime.date.today()
            time = datetime.datetime.now().strftime('%H:%M:%S')  
            rate = decimal.Decimal(c.get_rate(home_currency, target_currency))
            target_currency_amount = home_currency_amount*rate
            
            balance = {"EUR":user.profile.EUR, "USD":user.profile.USD}
            if home_currency_amount > balance[home_currency]:
                error = True
                return render(request, 'exchange.html', {'form': form, 'error':error, 'currency': home_currency})

            order = Order(date = date, time = time, user = username, home_currency=home_currency, home_currency_amount=home_currency_amount, rate=rate, target_currency=target_currency, target_currency_amount=target_currency_amount, status='pending')
            order.save()

        return redirect('/hello/')
    else:
        form = ExchangeForm()
    return render(request, 'exchange.html', {'form': form})


