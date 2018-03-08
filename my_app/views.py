# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.shortcuts import render
from django.contrib.auth import login, authenticate, logout 
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth.models import User as dbUser
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.generic import TemplateView
from models import Profile as DjProfile
from models import Order, CompleteOrders, Friendship, Notification
from my_app.forms import SignUpForm, TopUpForm, WithdrawForm, TransferForm, ExchangeForm
# Non-django imports
import os
import datetime
import decimal
from .tasks import exchange_celery
from lib import converter


# Views start here

#class HomeView(TemplateView):
#	template_name = 'index.html'

def HomeView(request):
    user=request.user
    notif=0
    if Notification.objects.filter(user=user):
        notif=1
    context_dict={'notif':notif}
    return render(request, 'index.html', context_dict)

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
def users(request):
    user_list = dbUser.objects.all()
    context_dict = {'user_list':user_list}
    return render(request, 'users.html', context_dict)

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

            # check if order can be matched to other users
            orderlist = Order.objects.filter(home_currency = order.target_currency, target_currency = order.home_currency)

            for order2 in orderlist:

                if order.status is not 'complete':
                    user2 = dbUser.objects.get(username=order2.user)
                    balance2 = {"EUR":user2.profile.EUR, "USD":user2.profile.USD, "RON":user2.profile.RON}

                    if order.home_currency_amount >= order2.target_currency_amount:
                        
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
              
        
	            else:

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
                    
@login_required
def addFriend(request):
    creator = request.user
    friend_name = request.GET.get('friend', '')
    friend = dbUser.objects.get(username=friend_name)
    if not Friendship.objects.filter(creator=creator, friend=friend):
        if Friendship.objects.filter(creator = friend, friend = creator).exists():
            friendship1 = Friendship.objects.get(creator=friend, friend=creator)
            friendship1.status = 'accepted'
            friendship2 = Friendship(creator=creator, friend=friend, status='accepted')
            friendship1.save()
        else:
            friendship2 = Friendship(creator=creator, friend=friend)
        friendship2.save()
    sent = True    
    context_dict = {'sent':sent}
    return render(request, 'users.html', context_dict)

@login_required
def friends(request):
    user = request.user
    friend_list = Friendship.objects.filter(creator=user, status='accepted')
    request_list = Friendship.objects.filter(creator=user, status='sent')
    context_dict = {'friend_list':friend_list, 'request_list':request_list}
    return render(request, 'friends.html', context_dict)

@login_required
def viewNotifications(request):
    user = request.user
    notifications = Notification.objects.filter(user = user)
    context_dict = {'notifications':notifications}
    response = render(request, 'notifications.html', context_dict) 
    Notification.objects.filter(user = user).delete()
    return render(request, 'notifications.html', context_dict)

