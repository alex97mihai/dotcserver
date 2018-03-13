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

@login_required
def HomeView(request):
    user=request.user
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications}
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
            balance = {'EUR': user.profile.EUR, 'RON': user.profile.RON, 'USD': user.profile.USD}
            currency = form.cleaned_data.get('currency')
            amount = form.cleaned_data.get('amount')
            if (amount > 0):
                balance[currency]=balance[currency] + amount
            user.profile.USD = balance['USD']
            user.profile.EUR = balance['EUR']
            user.profile.RON = balance['RON']
            user.save()
            return redirect('/')
    else:
        form = TopUpForm()
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications, 'form': form}
    return render(request, 'topup.html', context_dict)

@login_required
def withdraw(request):
    user = request.user
    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            balance = {'EUR': user.profile.EUR, 'RON': user.profile.RON, 'USD': user.profile.USD}
            currency = form.cleaned_data.get('currency')
            amount = form.cleaned_data.get('amount')
            if (amount > 0 and amount < balance[currency]):
                balance[currency]=balance[currency] - amount
            user.profile.USD = balance['USD']
            user.profile.EUR = balance['EUR']
            user.profile.RON = balance['RON']
            user.save()
            return redirect('/')
    else:
        form = WithdrawForm()
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications, 'form': form}
    return render(request, 'withdraw.html', context_dict)

@login_required
def transfer(request):
    user = request.user
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            # get user2, curency and amount from form
            uid = dbUser.objects.get(username=form.cleaned_data.get('username'))
            currency = form.cleaned_data.get('currency')
            amount = form.cleaned_data.get('amount')
            # dictionaries used for mapping the profiles of user1 and user2 to strings
            balance = {'EUR':user.profile.EUR, 'USD':user.profile.USD, 'RON':user.profile.RON}
            balance2 = {'EUR':uid.profile.EUR, 'USD':uid.profile.USD, 'RON':uid.profile.RON}
            # if user has enough money to transfer
            if amount >= 0 and balance[currency] >= amount:
                balance2[currency] = balance2[currency] + amount
                balance[currency] = balance[currency] - amount
            # update profiles using values saved in dictionary
            user.profile.EUR = balance['EUR']
            user.profile.RON = balance['RON']
            user.profile.USD = balance['USD']
            uid.profile.EUR = balance2['EUR']
            uid.profile.RON = balance2['RON']
            uid.profile.USD = balance2['USD']
            # save changes to database
            user.save()
            uid.save()
            # pop notification for user 2
            notification = Notification(user = uid, user2 = user, notification_type = 'transfer-complete', date = datetime.date.today(), time = datetime.datetime.now().strftime('%H:%M:%S'), notification = "You have received %s%s from %s" % (currency, str(amount), user.username))
            notification.save()

        return redirect('/')
    else:
        form = TransferForm()
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications, 'form': form}
    return render(request, 'transfer.html', context_dict)

@login_required
def viewRates(request):
    user = request.user
    c = converter.CurrencyRates()
    eurusd = c.get_rate('EUR', 'USD')
    eurron = c.get_rate('EUR', 'RON')
    ronusd = c.get_rate('RON', 'USD')
    roneur = c.get_rate('RON', 'EUR')
    usdron = c.get_rate('USD', 'RON')
    usdeur = c.get_rate('USD', 'EUR')
    notifications=Notification.objects.filter(user=user)
    context_dict = {'eurusd':eurusd, 'eurron':eurron, 'ronusd':ronusd, 'roneur':roneur, 'usdron':usdron, 'usdeur':usdeur, 'notifications':notifications}
    return render(request, 'rates.html', context_dict)

@login_required
def users(request):
    user = request.user
    user_list = dbUser.objects.all()
    notifications=Notification.objects.filter(user=user)
    context_dict = {'user_list':user_list, 'notifications':notifications}
    return render(request, 'users.html', context_dict)

@login_required
def exchange(request):
    user = request.user
    if request.method == 'POST':
        error = False
        c = converter.CurrencyRates()
        form = ExchangeForm(request.POST)
        if form.is_valid():

            # get user input
            home_currency = form.cleaned_data.get('home_currency')
            target_currency = form.cleaned_data.get('target_currency')
            home_currency_amount = decimal.Decimal(form.cleaned_data.get('home_currency_amount'))
            username = user.username
            date = datetime.date.today()
            time = datetime.datetime.now().strftime('%H:%M:%S')
            rate = decimal.Decimal(c.get_rate(home_currency, target_currency))
            target_currency_amount = home_currency_amount*rate

            # dictionary linking user profile to string values
            balance = {"EUR":user.profile.EUR, "USD":user.profile.USD, "RON":user.profile.RON}
            # check if user has enough funds to exchange and redirect back with error if not
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

        return redirect('/')
    else:
        form = ExchangeForm()
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications, 'form':form}
    return render(request, 'exchange.html', context_dict)

@login_required
def historyView(request):
    user = request.user
    orders = Order.objects.filter(user=user.username, status='pending')
    completed_orders = CompleteOrders.objects.filter(user=user.username)
    notifications=Notification.objects.filter(user=user)
    context_dict = {'orders':orders, 'completed_orders':completed_orders, 'notifications':notifications}
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
            notification1 = Notification(user=friend, user2 = creator, notification_type = "friend-accept", date = datetime.date.today(), time = datetime.datetime.now().strftime('%H:%M:%S'), notification="You are now friends with %s" % creator.username)
            notification2 = Notification(user=creator, user2 = friend, notification_type = "friend-accept", date = datetime.date.today(), time = datetime.datetime.now().strftime('%H:%M:%S'), notification="You are now friends with %s" % friend.username)
            notification1.save()
            notification2.save()
        else:
            friendship2 = Friendship(creator=creator, friend=friend)
            notification = Notification(user=friend, user2 = creator, notification_type = "friend-request", date = datetime.date.today(), time = datetime.datetime.now().strftime('%H:%M:%S'), notification="You have a friend request from %s" % creator.username)
            notification.save()
        friendship2.save()

    sent = True
    context_dict = {'sent':sent}
    return redirect('/friends/')

@login_required
def friends(request):
    user = request.user
    friend_list = Friendship.objects.filter(creator=user, status='accepted')
    request_list = Friendship.objects.filter(friend=user, status='sent')
    pending_list = Friendship.objects.filter(creator=user, status='sent')
    notifications=Notification.objects.filter(user=user)
    context_dict = {'friend_list':friend_list, 'request_list':request_list, 'pending_list':pending_list, 'notifications':notifications}
    return render(request, 'friends.html', context_dict)

@login_required
def viewNotifications(request):
    user = request.user
    notifications = Notification.objects.filter(user = user)
    context_dict = {'notifications':notifications}
    response = render(request, 'notifications.html', context_dict)
    Notification.objects.filter(user = user).delete()
    return render(request, 'notifications.html', context_dict)





### AJAX VIEWS ###

def get_notifications(request):
    if request.is_ajax():
        user = request.user
        notifications = Notification.objects.filter(user = user)
        return render(request, 'ajax/get_notifications.html', {'notifications': notifications})
    else:
        return redirect ('/')

def notiflength(request):
    if request.is_ajax():
        user = request.user
        notifications = Notification.objects.filter(user = user, status='unseen')
        return render(request, 'ajax/notiflength.html', {'notifications': notifications})
    else:
        return redirect ('/')

def mark_as_clear(request):
    if request.is_ajax():
        user = request.user
        notifications = Notification.objects.filter(user = user, status='unseen')
        for notification in notifications:
            notification.status='seen'
            notification.save()
    else:
        return redirect ('/')
