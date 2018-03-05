# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import decimal
import datetime
from django.shortcuts import render

from django.contrib.auth import login, authenticate, logout 
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from my_app.forms import SignUpForm, TopUpForm, WithdrawForm, TransferForm, ExchangeForm
from models import Profile as DjProfile
from models import Order, CompleteOrders
from django.contrib.auth.models import User as dbUser
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# Non-django imports
from .tasks import test_celery
from lib import converter
# Create your views here.

from django.views.generic import TemplateView



class HomeView(TemplateView):
	template_name = 'index.html'


def logoutView(request):
    logout(request)
    return redirect('/hello/')



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

@login_required
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
	    if (form.cleaned_data.get('RON') > 0):
		user.profile.RON = user.profile.RON + form.cleaned_data.get('RON')
		user.save()
            return redirect('/hello/')
    else:
        form = TopUpForm()
    return render(request, 'topup.html', {'form': form})

@login_required
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
	    if (form.cleaned_data.get('RON') > 0):
		user.profile.RON = user.profile.RON - form.cleaned_data.get('RON')
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
        if form.is_valid():
            # get user by username
            uid = dbUser.objects.get(username=form.cleaned_data.get('username'))
            
            EURtr = form.cleaned_data.get('EUR')
            USDtr = form.cleaned_data.get('USD')
            RONtr = form.cleaned_data.get('RON')
	    # if user has enough EUR to transfer
            if EURtr >= 0 and user.profile.EUR >= EURtr:
                uid.profile.EUR = uid.profile.EUR + EURtr
                user.profile.EUR = user.profile.EUR - EURtr

            if USDtr >= 0 and user.profile.USD >= USDtr:
                uid.profile.USD = uid.profile.USD + USDtr
                user.profile.USD = user.profile.USD - USDtr
	  
 	    if RONtr >= 0 and user.profile.RON >= RONtr:
		uid.profile.RON = uid.profile.RON + RONtr
                user.profile.RON = user.profile.RON - RONtr
 
            user.save()
            uid.save()
        
        return redirect('/hello/')
    else:
        form = TransferForm()
    return render(request, 'transfer.html', {'form': form})

@login_required
def viewRates(request):
    c = converter.CurrencyRates()
    eurrate  = c.get_rate('EUR', 'USD')
    usdrate  = c.get_rate('USD', 'EUR')
    context_dict = {'eurrate': eurrate, 'usdrate': usdrate}
    return render(request, 'rates.html', context_dict)

@login_required
def exchange(request):
    if request.method == 'POST':
        error = False
        user = request.user
        c = converter.CurrencyRates()
        form = ExchangeForm(request.POST)
        if form.is_valid():

            # get user input and store it
            home_currency = form.cleaned_data.get('home_currency')
            target_currency = form.cleaned_data.get('target_currency')
            home_currency_amount = decimal.Decimal(form.cleaned_data.get('home_currency_amount'))
            username = user.username
            date = datetime.date.today()
            time = datetime.datetime.now().strftime('%H:%M:%S')  
            rate = decimal.Decimal(c.get_rate(home_currency, target_currency))
            target_currency_amount = home_currency_amount*rate
            
            # dictionary linking string to variable
            balance = {"EUR":user.profile.EUR, "USD":user.profile.USD, "RON":user.profile.RON}
            # check if user has enough funds to exchange and return error if not
            if home_currency_amount > balance[home_currency]:
                error = True
                return render(request, 'exchange.html', {'form': form, 'error':error, 'currency': home_currency})

            # create Order object from user input
            order = Order(date = date, time = time, user = username, home_currency=home_currency, home_currency_amount=home_currency_amount, rate=rate, target_currency=target_currency, target_currency_amount=target_currency_amount, status='pending', home_backup=home_currency_amount, target_backup=target_currency_amount)
            
            order.save()
            out = open('/home/ubuntu/myproject/log.txt', 'w')

            # check if order can be matched to other users
            orderlist = Order.objects.filter(home_currency = order.target_currency, target_currency = order.home_currency)

            for order2 in orderlist:

                if order.status is not 'complete':
                    user2 = dbUser.objects.get(username=order2.user)
                    out.write('user 1 is %s and user 2 is %s' % (str(user),str(user2)))
                    balance2 = {"EUR":user2.profile.EUR, "USD":user2.profile.USD, "RON":user2.profile.RON}
                    out.write('\n before the transaction, user 1 had %s EUR and %s USD' % (str(balance['EUR']), str(balance['USD'])))
                    out.write('\n before the transaction, user 2 had %s EUR and %s USD' % (str(balance2['EUR']), str(balance2['USD'])))
                    out.write('\nuser 1 is looking to exchange %s%s for %s%s' % (str(order.home_currency_amount), str(order.home_currency), str(order.target_currency_amount),str(order.target_currency)))
                    out.write('\nuser 2 is looking to exchange %s%s for %s%s' % (str(order2.home_currency_amount), str(order2.home_currency), str(order2.target_currency_amount), str(order2.target_currency)))

                    if order.home_currency_amount >= order2.target_currency_amount:
                        out.write('\n we are now inside the if: user 1 is selling more of his currency than user 2 is looking to buy')
                        
                        # user 1 is selling more currency than user 2, so the .home field of his profile will be updated to .home-how much 2 is buying
                        # using order1.home as reference
                        # updating the profile of user1
                        balance[str(order.home_currency)]=balance[str(order.home_currency)]-order2.target_currency_amount
                        # updating the order of user1
                        order.home_currency_amount = order.home_currency_amount - order2.target_currency_amount
                        # updating the profile of user2
                        balance2[str(order2.target_currency)]=balance2[str(order2.target_currency)] + order2.target_currency_amount
                        # updating the order of user 2
                        order2.target_currency_amount = 0
                        # using order2.home as reference
                        # updating the profile of user1
                        balance[str(order.target_currency)]=balance[str(order.target_currency)] + order2.home_currency_amount
                        # updating the order of user1
                        order.target_currency_amount = order.target_currency_amount - order2.home_currency_amount
                        # updating the profile of user2
                        balance2[str(order2.home_currency)] = balance2[str(order2.home_currency)] - order2.home_currency_amount
                        # updating the order of user2
                        order2.home_currency_amount = 0
              
                        out.write('\n after the transaction, user 1 has %s%s and %s%s' % (balance[str(order.home_currency)], str(order.home_currency), balance[str(order.target_currency)], str(order.target_currency)))
                        out.write('\n after the transaction, user 2 has %s%s and %s%s' % (balance2[str(order2.home_currency)], str(order2.home_currency), balance2[str(order2.target_currency)], str(order2.target_currency)))
                        out.write('\n user 1 order still has %s%s to exchange for %s%s' % (str(order.home_currency_amount), str(order.home_currency), str(order.target_currency_amount), str(order.target_currency)))
                        out.write('\n user2 order still has %s%s to exchange for %s%s' % (str(order2.home_currency_amount), str(order2.home_currency), str(order2.target_currency_amount), str(order2.target_currency)))
        
	            else:
                        out.write('\n we are now inside the else: user 1 is selling less of his currency than user 2 is looking to buy')

                        # using order1.home as reference
                        # updating the profile of user 1
                        balance[str(order.home_currency)]=balance[str(order.home_currency)] - order.home_currency_amount

                        #updating the profile of user 2
                        balance2[str(order2.target_currency)] = balance2[str(order2.target_currency)] + order.home_currency_amount

                        #updating the order of user2
                        order2.target_currency_amount = order2.target_currency_amount - order.home_currency_amount
                      
                        # updating the order of user 1
                        order.home_currency_amount = 0

                        #using order2.home as reference
                        #updating the profile of user 1
                        balance[str(order.target_currency)] = balance[str(order.target_currency)] + order.target_currency_amount
                        #updating the profile of user 2
                        balance2[str(order2.home_currency)] = balance2[str(order2.home_currency)] - order.target_currency_amount
                        #ypdating the order of user 2
                        order2.home_currency_amount = order2.home_currency_amount - order.target_currency_amount
                        #updating the order of user 1
                        order.target_currency_amount = 0

                        out.write('\n after the transaction, user 1 has %s%s and %s%s' % (balance[str(order.home_currency)], str(order.home_currency), balance[str(order.target_currency)], str(order.target_currency)))
                        out.write('\n after the transaction, user 2 has %s%s and %s%s' % (balance2[str(order2.home_currency)], str(order2.home_currency), balance2[str(order2.target_currency)], str(order2.target_currency)))
                        out.write('\n user 1 order still has %s%s to exchange for %s%s' % (str(order.home_currency_amount), str(order.home_currency), str(order.target_currency_amount), str(order.target_currency)))
                        out.write('\n user2 order still has %s%s to exchange for %s%s' % (str(order2.home_currency_amount), str(order2.home_currency), str(order2.target_currency_amount), str(order2.target_currency)))



                    # saving changes to user profiles
                    user.profile.USD = balance['USD']
                    user.profile.EUR = balance['EUR']
		    user.profile.RON = balance['RON']
                    user.save()
                            
                    user2.profile.USD = balance2['USD']    
                    user2.profile.EUR = balance2['EUR']
		    user2.profile.RON = balance2['RON']
                    user2.save()
                        
                    # saving changes to orders
                    if order.home_currency_amount == 0: 
                        order.status = 'complete'
                    if order2.home_currency_amount == 0:
                        order2.status = 'complete'
                    order.save()
                    order2.save()

        out.close()

        return redirect('/hello/')
    else:
        form = ExchangeForm()
    return render(request, 'exchange.html', {'form': form})

@login_required
def historyView(request):
    user = request.user
    orders = Order.objects.filter(user=user.username, status='pending')
    completed_orders = CompleteOrders.objects.filter(user=user.username)
    context_dict = {'orders':orders, 'completed_orders':completed_orders}
    return render(request, 'history.html', context_dict)
                    



