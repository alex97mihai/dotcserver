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
from models import Order, CompleteOrders, Friendship, Notification, Card, Message, Product, PurchasedItem, Cart
from my_app.forms import *
from django.utils import timezone
# Non-django imports
import json
import os
import datetime
import decimal
import time
from .tasks import exchange_celery
from lib import converter

# Views start here

@login_required
def HomeView(request):
    user=request.user
    if user.profile.corporate is False:
        notifications=Notification.objects.filter(user=user)
        context_dict={'notifications':notifications}
        return render(request, 'profile.html', context_dict)
    else:
        return render(request, 'companyProfile.html')

@login_required
def walletView(request):
    user=request.user
    if user.profile.corporate is False:
        context_dict={'user':user}
        return render(request, 'wallet.html', context_dict)
    else:
        return render(request, 'companyWallet.html')

@login_required
def profileView(request):
    user=request.user
    context_dict={'user':user}
    return render(request, 'profile.html', context_dict)

def logoutView(request):
    logout(request)
    return redirect('/')

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
            return redirect('/')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def corporateSignup(request):
    if request.method == 'POST':
	form = SignUpForm(request.POST)
	if form.is_valid():
	    user = form.save()
            user.refresh_from_db()
	    user.profile.corporate = True
	    user.save()
            raw_password = form.cleaned_data.get('password1')
	    user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect('/')
    else:
	form = SignUpForm()
    return render(request, 'CorporateSignup.html', {'form': form})

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
            return redirect('/wallet/')
    else:
        form = TopUpForm()
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications, 'form': form}
    return render(request, 'topup.html', context_dict)

@login_required
def addProduct(request):
    user = request.user
    if user.profile.corporate is True:
        if request.method == 'POST':
            form = AddProduct(request.POST)
            if form.is_valid():
                newProduct = Product()
                newProduct.user = user
                newProduct.name = form.cleaned_data.get('name')
                newProduct.p_id = form.cleaned_data.get('p_id')
                newProduct.p_type = form.cleaned_data.get('p_type')
                newProduct.price = form.cleaned_data.get('price')
                newProduct.currency = form.cleaned_data.get('currency')
                newProduct.date = datetime.date.today()
                newProduct.time = datetime.datetime.now().strftime('%H:%M:%S')
                newProduct.save()
                return redirect('/products')
        else:
            form = AddProduct()
            products = Product.objects.filter(user=user).order_by('-id')[:15]
            context_dict={'form': form, 'products': products}
            return render(request, 'products.html', context_dict)
    else:
        return redirect ('/')

@login_required
def BuyProductView(request):
    user = request.user
    if user.profile.corporate is False:
        category = request.GET.get('category', '')
        products = Product.objects.filter(p_type=category)
        context_dict = {'products': products}
        if request.GET.get('add', ''):
            django_id = request.GET.get('add', '')
            if not Cart.objects.filter(user=user, product=Product.objects.filter(id=django_id)).exists():
                cart = Cart(user=user, product=Product.objects.get(id=django_id), quantity=1)
                cart.save()
        full_cart = Cart.objects.filter(user=user).distinct()
        context_dict['full_cart']=full_cart

        return render(request, 'buy.html', context_dict)

    else:
        return redirect('/')

@login_required
def CartView(request):
    user = request.user
    total = {'EUR': 0, 'USD': 0, 'RON': 0}
    if user.profile.corporate is False:
        # if user is removing an item
        if request.GET.get('rm', ''):
            removedID = request.GET.get('rm', '')
            product = Product.objects.filter(p_id = removedID)
            Cart.objects.filter(product = product).delete()
        products = Cart.objects.filter(user = user).order_by('-id')
        for item in products:
            total[item.product.currency] = total[item.product.currency] + item.product.price
        context_dict = {'products': products, 'total': total}
        return render(request, 'cart.html', context_dict)
    else:
        return redirect ('/')

@login_required
def CheckoutView(request):
    error = 0
    user = request.user
    # dictionaries for balance, total cart value and result
    result = {}
    total = {'EUR': 0, 'USD': 0, 'RON': 0}
    balance = {'EUR': user.profile.EUR, 'USD': user.profile.USD, 'RON': user.profile.RON}
    if user.profile.corporate is False:
        # get cart
        products = Cart.objects.filter(user = user).order_by('-id')
        # get cart value
        for item in products:
            total[item.product.currency] = total[item.product.currency] + item.product.price
        # get remaining money after payment
        for key in total:
            result[key]=balance[key]-total[key]
        # check if user has enough money and pop error if not
        for key in result:
            if result[key]<0:
                error = 1
                context_dict = {'error': error}
                # stop here and show the error
                return render(request, 'checkout.html', context_dict)
        # if user has enough money
        if not error:
            user.profile.EUR = result['EUR']
            user.profile.USD = result['USD']
            user.profile.RON = result['RON']
            user.save()
            # save the purchase in the database
            for item in products:
                purchased_item = PurchasedItem(name=item.product.name, user=user, seller=item.product.user, p_id=item.product.p_id, p_type=item.product.p_type, price=item.product.price, currency=item.product.currency, date=datetime.date.today(), time=datetime.datetime.now().strftime('%H:%M:%S'))
                purchased_item.save()
            # empty cart
            Cart.objects.filter(user = user).delete()
        context_dict = {'error': error}
        return render(request, 'checkout.html', context_dict)
    # not for companies
    else:
        return redirect ('/')



@login_required
def sales(request):
    user = request.user
    if user.profile.corporate is True:
        # get sales list
        products = PurchasedItem.objects.filter(seller = user).order_by('-id')
        context_dict = {'products': products}
        return render(request, 'sales.html', context_dict)
    # not for users
    else:
        return redirect ('/')


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
            return redirect('/wallet/')
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

        return redirect('/wallet/')
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

        return redirect('/wallet/')
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
    action = request.GET.get('accepted', '')
    friend = dbUser.objects.get(username=friend_name)
    if (action=='false'):
        Friendship.objects.filter(creator=friend, friend=creator).delete()
        return redirect('/friends/')
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
def terms(request):
    user = request.user
    notifications=Notification.objects.filter(user=user)
    context_dict = {'notifications':notifications}
    return render(request, 'terms.html', context_dict)


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


@login_required
def uploadPic(request):
    user = request.user
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            user.profile.avatar=form.cleaned_data['image']
            user.save()
        return redirect('/wallet/')
    else:
        form = ImageUploadForm()
        notifications=Notification.objects.filter(user=user)
        context_dict={'notifications':notifications, 'form':form}
        if user.profile.corporate is False:
            return render(request, 'uploadPic.html', context_dict)
        else:
            return render(request, 'corporateuploadPic.html', context_dict)


@login_required
def addCard(request):
    user = request.user
    if request.method == 'POST':
        form = AddCardForm(request.POST)
        if form.is_valid():
            card = Card()
            card.user = user
            card.number = form.cleaned_data.get('number')
            card.csv = form.cleaned_data.get('csv')
            card.exp_date = form.cleaned_data.get('exp_date')
            card.name = form.cleaned_data.get('name')
            card.address = form.cleaned_data.get('address')
            card.phone = form.cleaned_data.get('phone')
            card.c_currency = form.cleaned_data.get('c_currency')
            if (card.number[0]=='4'):
                card.provider = 'Visa'
            elif (card.number[0]=='5'):
                card.provider = 'MasterCard'
            elif (card.number[0]=='3'):
                card.provider = 'American Express'
            else:
                card.provider = 'Unknown'
            card.save()
        return redirect('/cards/')
    else:
        if(request.GET.get('card', '')):
            default_new = request.GET.get('card', '')
            user.profile.default_payment = int(default_new)
            user.save()
        form = AddCardForm()
        cards = Card.objects.filter(user=user)
        for available_card in cards:
            available_card.number = available_card.number[-4:]
        notifications=Notification.objects.filter(user=user)
        if (request.GET.get('rm', '')):
            rm = request.GET.get('rm', '')
            if (Card.objects.filter(pk=int(rm), user=user).exists()):
                Card.objects.get(pk=int(rm)).delete()
                cards = Card.objects.filter(user=user)
        context_dict={'notifications':notifications, 'form':form, 'cards':cards}
        return render(request, 'cards.html', context_dict)


@login_required
def Settings(request):
    user = request.user
    if user.profile.corporate is False:
        notifications=Notification.objects.filter(user=user)
        context_dict={'notifications':notifications}
        return render(request, 'settings.html', context_dict)
    else:
        return render(request, 'companysettings.html')


@login_required
def SendMessage(request):

    if (request.GET.get('friend', '')):
        user = request.user
        user_to_usrname = request.GET.get('friend', '')
        if User.objects.filter(username=user_to_usrname).exists():
                user_to = User.objects.get(username=user_to_usrname)
                messages=Message.objects.filter(user_from=user, user_to=user_to) | Message.objects.filter(user_from=user_to, user_to=user)
                messages=messages.order_by('pk')
                notifications = Notification.objects.filter(user=user)
                form=SendMessageForm()
                context_dict={'notifications':notifications, 'messages':messages, 'form':form, 'user2':user_to_usrname}

                return render(request, 'chat.html', context_dict)
        else:
            return redirect('/friends/')


    user = request.user
    if request.method == 'POST':
        form = SendMessageForm(request.POST)
        if form.is_valid():
            error = False
            message = Message()
            message.user_from = user
            if User.objects.filter(username=form.cleaned_data.get('user_to')).exists():
                message.user_to = User.objects.get(username=form.cleaned_data.get('user_to'))
            else:
                notifications = Notification.objects.filter(user=user)
                messages_from = Message.objects.filter(user_from=user)
                messages_to = Message.objects.filter(user_to=user)
                error = True
                context_dict={'notifications':notifications, 'form':form, 'messages_from':messages_from, 'messages_to':messages_to, 'error':error}
                return render(request, 'messages.html', context_dict)
            message.message = form.cleaned_data.get('message')
            message.date = datetime.date.today()
            message.time = datetime.datetime.now().strftime('%H:%M:%S')
            message.status = "sent"
            message.save()
        return redirect('/messages/')
    else:
        form = SendMessageForm()
        notifications = Notification.objects.filter(user=user)

        messages_from = Message.objects.filter(user_from=user)
        messages_to = Message.objects.filter(user_to=user)
        user_list = Friendship.objects.filter(creator=user)
        context_dict={'notifications':notifications, 'form':form, 'messages_from':messages_from, 'messages_to':messages_to, 'user_list':user_list}
        if user.profile.corporate is False:
            return render(request, 'messages.html', context_dict)
        else:
            return render(request, 'companymessages.html', context_dict)



### AJAX VIEWS ###

def send_message(request):
    if request.method == 'POST':
        message_text = request.POST.get('the_message')
        user2=request.POST.get('user2')
        response_data = {}
        message = Message(message=message_text, user_from=request.user, user_to=User.objects.get(username=user2))
        message.date = datetime.date.today()
        message.time = datetime.datetime.now().strftime('%H:%M:%S')

        message.save()

        response_data['result'] = 'Create post successful!'
        response_data['postpk'] = message.pk
        response_data['text'] = message.message
        response_data['author'] = message.user_from.username

        return HttpResponse(
            json.dumps(response_data),
            content_type="application/json"
        )
    else:
        return HttpResponse(
            json.dumps({"nothing to see": "this isn't happening"}),
            content_type="application/json"
        )

def get_messages(request):
    user = request.user
    user_to_usrname = request.GET.get('user2')
    if User.objects.filter(username=user_to_usrname).exists():
        user_to = User.objects.get(username=user_to_usrname)
        messages=Message.objects.filter(user_from=user, user_to=user_to, status_back="sending") | Message.objects.filter(user_from=user_to, user_to=user, status="sending")
        messages=messages.order_by('pk')
        for message in messages:
            if (user == message.user_to):
                message.status = 'seen'
                message.save()
            else:
                message.status_back = 'seen'
                message.save()

    return render(request, 'ajax/message_list.html', {'messages': messages})


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

def messlength(request):
    if request.is_ajax():
        user = request.user
        messages = Message.objects.filter(user_to=user, status='sending')
        return render(request, 'ajax/messlength.html', {'messages': messages})
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
