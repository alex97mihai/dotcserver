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
from django.db.models import Count
from models import Profile as DjProfile
from models import Order, CompleteOrders, Message, Product, PurchasedItem, Cart, TransferHistory
from models import Document, Post, OpHistory, Friendship, Notification, Card, CampaignItem
from my_app.forms import *
from django.utils import timezone
# Non-django imports
import json, os, datetime, decimal, time, csv, codecs
import _strptime
from .tasks import exchange_celery
from lib import converter


# Views start here

@login_required
def homeView(request):
    user=request.user
    if user.profile.corporate is False:
        return render(request, 'users/profile/profile.html')
    else:
        return render(request, 'corporate/corporate-profile.html')

@login_required
def walletView(request):
    user=request.user
    if user.profile.corporate is False:
        context_dict={'user':user}
        return render(request, 'users/wallet/wallet.html', context_dict)
    else:
        return render(request, 'corporate/corporate-wallet.html')

@login_required
def profileView(request):
    user=request.user
    context_dict={'user':user}
    return render(request, 'profile.html', context_dict)

def logoutView(request):
    logout(request)
    return redirect('/')

def signupView(request):
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
    return render(request, 'registration/signup.html', {'form': form})

def corporateSignupView(request):
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
    return render(request, 'corporate/registration/corporate-signup.html', {'form': form})


@login_required
def topupView(request):
    user = request.user
    if user.profile.corporate is False:
        if request.method == 'POST':
            form = TopUpForm(request.POST)
            if form.is_valid():
                balance = {'EUR': user.profile.EUR, 'RON': user.profile.RON, 'USD': user.profile.USD}
                currency = form.cleaned_data.get('currency')
                amount = form.cleaned_data.get('amount')
                if (amount > 0):
                    balance[currency]=balance[currency] + amount
                    HistoryItem = OpHistory(user = user,
                                            currency= currency,
                                            amount=amount,
                                            optype='topup',
                                            date=datetime.date.today(),
                                            time=datetime.datetime.now().strftime('%H:%M:%S'))
                    HistoryItem.save()
                user.profile.USD = balance['USD']
                user.profile.EUR = balance['EUR']
                user.profile.RON = balance['RON']
                user.save()
                return redirect('/wallet/')
        else:
            form = TopUpForm()
        context_dict={'form': form}
        return render(request, 'users/wallet/topup.html', context_dict)
    else:
        return redirect ('/')

@login_required
def addProductView(request):
    user = request.user
    if user.profile.corporate is True:
        if request.method == 'POST':
            form = AddProduct(request.POST)
            if form.is_valid():
                newProduct = Product(user = user,
                                     name = form.cleaned_data.get('name'),
                                     p_id = form.cleaned_data.get('p_id'),
                                     p_type = form.cleaned_data.get('p_type'),
                                     price = form.cleaned_data.get('price'),
                                     currency = form.cleaned_data.get('currency'),
                                     date = datetime.date.today(),
                                     time = datetime.datetime.now().strftime('%H:%M:%S'))
                newProduct.save()
                return redirect('/products')
        else:
            form = AddProduct()
            products = Product.objects.filter(user=user).order_by('-id')[:15]
            context_dict={'form': form, 'products': products}
            return render(request, 'corporate/corporate-products.html', context_dict)
    else:
        return redirect ('/')



@login_required
def buyProductView(request):
    user = request.user
    if user.profile.corporate is False:
        category = request.GET.get('category', '')
        products = Product.objects.filter(p_type=category)
        context_dict = {'products': products}
        # user is adding a product to cart
        if request.GET.get('add', ''):
            django_id = request.GET.get('add', '')
            if not Cart.objects.filter(user=user, product=Product.objects.filter(id=django_id)).exists():
                cart = Cart(user=user, product=Product.objects.get(id=django_id), quantity=1)
                cart.save()
        full_cart = Cart.objects.filter(user=user).distinct()
        categories = Product.objects.order_by().values_list('p_type').distinct()
        categories_string = [x[0] for x in categories]
        context_dict['full_cart']=full_cart
        context_dict['categories_string']=categories_string
        return render(request, 'users/shop/buy.html', context_dict)

    else:
        return redirect('/')

@login_required
def cartView(request):
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
        context_dict = {'products': products, 'total': total, 'user': user}
        return render(request, 'users/shop/cart.html', context_dict)
    else:
        return redirect ('/')

@login_required
def checkoutView(request):
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
                return render(request, 'users/shop/checkout.html', context_dict)
        # if user has enough money
        if not error:
            user.profile.EUR = result['EUR']
            user.profile.USD = result['USD']
            user.profile.RON = result['RON']
            user.save()
            # save the purchase in the database
            for item in products:
                balance2 = {'EUR': item.product.user.profile.EUR, 'USD': item.product.user.profile.USD, 'RON': item.product.user.profile.RON}
                purchased_item = PurchasedItem(name=item.product.name,
                                               user=user,
                                               seller=item.product.user,
                                               p_id=item.product.p_id,
                                               dj_id=item.product.id,
                                               p_type=item.product.p_type,
                                               price=item.product.price,
                                               currency=item.product.currency,
                                               date=datetime.date.today(),
                                               time=datetime.datetime.now().strftime('%H:%M:%S'))
                purchased_item.save()
                balance2[item.product.currency] = balance2[item.product.currency] + item.product.price
                item.product.user.profile.EUR = balance2['EUR']
                item.product.user.profile.USD = balance2['USD']
                item.product.user.profile.RON = balance2['RON']
                item.product.user.save()
            # empty cart
            Cart.objects.filter(user = user).delete()
        context_dict = {'error': error}
        return render(request, 'users/shop/checkout.html', context_dict)
    # not for companies
    else:
        return redirect ('/')



@login_required
def salesView(request):
    user = request.user
    if user.profile.corporate is True:
        # get sales list
        products = PurchasedItem.objects.filter(seller = user).order_by('-id')
        context_dict = {'products': products}
        return render(request, 'corporate/corporate-sales.html', context_dict)
    # not for users
    else:
        return redirect ('/')


@login_required
def withdrawView(request):
    user = request.user
    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            balance = {'EUR': user.profile.EUR, 'RON': user.profile.RON, 'USD': user.profile.USD}
            currency = form.cleaned_data.get('currency')
            amount = form.cleaned_data.get('amount')
            if (amount > 0 and amount <= balance[currency]):
                balance[currency]=balance[currency] - amount
                HistoryItem = OpHistory(user = user,
                                        currency= currency,
                                        amount=amount,
                                        optype='withdraw',
                                        date=datetime.date.today(),
                                        time=datetime.datetime.now().strftime('%H:%M:%S'))
                HistoryItem.save()
            user.profile.USD = balance['USD']
            user.profile.EUR = balance['EUR']
            user.profile.RON = balance['RON']
            user.save()
            return redirect('/wallet/')
    else:
        form = WithdrawForm()
    notifications=Notification.objects.filter(user=user)
    context_dict={'notifications':notifications, 'form': form}
    return render(request, 'users/wallet/withdraw.html', context_dict)

@login_required
def transferView(request):
    user = request.user
    if user.profile.corporate is False:
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
                    HistoryList = TransferHistory(user = user,
                                                  user2 = uid,
                                                  currency = currency,
                                                  amount = amount,
                                                  date = datetime.date.today(),
                                                  time = datetime.datetime.now().strftime('%H:%M:%S') )
                    HistoryList.save()
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
        return render(request, 'users/wallet/transfer.html', context_dict)
    else:
        return redirect('/')

@login_required
def viewRatesView(request):
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
    return render(request, 'users/wallet/rates.html', context_dict)

@login_required
def usersView(request):
    user = request.user
    user_list = dbUser.objects.all()
    notifications=Notification.objects.filter(user=user)
    context_dict = {'user_list':user_list, 'notifications':notifications}
    return render(request, 'users/chat/users.html', context_dict)

@login_required
def exchangeView(request):
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
                return render(request, 'users/wallet/exchange.html', {'form': form, 'error':error, 'currency': home_currency})

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
                        #updating the order of user 2
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
    return render(request, 'users/wallet/exchange.html', context_dict)

@login_required
def historyView(request):
    user = request.user
    if user.profile.corporate is False:
        orders = Order.objects.filter(user=user.username, status='pending')
        completed_orders = CompleteOrders.objects.filter(user=user.username)
        notifications=Notification.objects.filter(user=user)
        HistoryList = OpHistory.objects.filter(user=user)
        TransferList = TransferHistory.objects.filter(user=user) | TransferHistory.objects.filter(user2=user)
        PaymentList = PurchasedItem.objects.filter(user=user)
        context_dict = {'PaymentList':PaymentList, 'orders':orders, 'completed_orders':completed_orders, 'notifications':notifications, 'HistoryList': HistoryList, 'TransferList': TransferList}
        return render(request, 'users/wallet/history.html', context_dict)
    else:
        return redirect('/')

@login_required
def addFriendView(request):
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
            notification1 = Notification(user=friend,
                                         user2 = creator,
                                         notification_type = "friend-accept",
                                         date = datetime.date.today(),
                                         time = datetime.datetime.now().strftime('%H:%M:%S'),
                                         notification="You are now friends with %s" % creator.username)
            notification2 = Notification(user=creator,
                                         user2 = friend,
                                         notification_type = "friend-accept",
                                         date = datetime.date.today(),
                                         time = datetime.datetime.now().strftime('%H:%M:%S'),
                                         notification="You are now friends with %s" % friend.username)
            notification1.save()
            notification2.save()
        else:
            friendship2 = Friendship(creator=creator, friend=friend)
            notification = Notification(user=friend,
                                        user2 = creator,
                                        notification_type = "friend-request",
                                        date = datetime.date.today(),
                                        time = datetime.datetime.now().strftime('%H:%M:%S'),
                                        notification="You have a friend request from %s" % creator.username)
            notification.save()
        friendship2.save()

    sent = True
    context_dict = {'sent':sent}
    return redirect('/friends/')


@login_required
def termsView(request):
    user = request.user
    notifications=Notification.objects.filter(user=user)
    context_dict = {'notifications':notifications}
    return render(request, 'etc/terms.html', context_dict)


@login_required
def friendsView(request):
    user = request.user
    friend_list = Friendship.objects.filter(creator=user, status='accepted')
    request_list = Friendship.objects.filter(friend=user, status='sent')
    pending_list = Friendship.objects.filter(creator=user, status='sent')
    notifications=Notification.objects.filter(user=user)
    context_dict = {'friend_list':friend_list, 'request_list':request_list, 'pending_list':pending_list, 'notifications':notifications}
    return render(request, 'users/chat/friends.html', context_dict)

@login_required
def uploadPicView(request):
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
            return render(request, 'users/profile/upload-pic.html', context_dict)
        else:
            return render(request, 'corporate/corporate-picture.html', context_dict)


@login_required
def addCardView(request):
    user = request.user
    if user.profile.corporate is False:
        # is user adding a card?
        if request.method == 'POST':
            form = AddCardForm(request.POST)
            if form.is_valid():
                card = Card(user = user,
                            number = form.cleaned_data.get('number'),
                            csv = form.cleaned_data.get('csv'),
                            exp_date = form.cleaned_data.get('exp_date'),
                            name = form.cleaned_data.get('name'),
                            address = form.cleaned_data.get('address'),
                            phone = form.cleaned_data.get('phone'),
                            c_currency = form.cleaned_data.get('c_currency'))
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
        # display existing cards
        else:
            # if user is changing default card
            if(request.GET.get('card', '')):
                default_new = request.GET.get('card', '')
                user.profile.default_payment = int(default_new)
                user.save()
            form = AddCardForm()
            # get a lsit of all existing cards
            cards = Card.objects.filter(user=user)
            # hide all but the last 4 digits
            for available_card in cards:
                available_card.number = available_card.number[-4:]
            # if user is removing a card
            if (request.GET.get('rm', '')):
                rm = request.GET.get('rm', '')
                if (Card.objects.filter(pk=int(rm), user=user).exists()):
                    Card.objects.get(pk=int(rm)).delete()
                    cards = Card.objects.filter(user=user)
            notifications=Notification.objects.filter(user=user)
            context_dict={'notifications':notifications, 'form':form, 'cards':cards}
            return render(request, 'users/profile/cards.html', context_dict)
    else:
        return redirect('/')


@login_required
def settingsView(request):
    user = request.user
    if user.profile.corporate is False:
        notifications=Notification.objects.filter(user=user)
        context_dict={'notifications':notifications}
        return render(request, 'users/profile/settings.html', context_dict)
    else:
        return render(request, 'corporate/corporate-settings.html')


@login_required
def sendMessageView(request):
    # user entering a chat with a friend
    if (request.GET.get('friend', '')):
        user = request.user
        user_to_usrname = request.GET.get('friend', '')
        # does that user exist?
        if User.objects.filter(username=user_to_usrname).exists():
                user_to = User.objects.get(username=user_to_usrname)
                # get existing messages
                messages=Message.objects.filter(user_from=user, user_to=user_to) | Message.objects.filter(user_from=user_to, user_to=user)
                messages=messages.order_by('pk')
                notifications = Notification.objects.filter(user=user)
                form=SendMessageForm()
                context_dict={'notifications':notifications, 'messages':messages, 'form':form, 'user2':user_to_usrname}

                return render(request, 'users/chat/chat.html', context_dict)
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
                return render(request, 'users/chat/messages.html', context_dict)
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
            return render(request, 'users/chat/messages.html', context_dict)
        else:
            return render(request, 'corporate/corporate-messages.html', context_dict)

@login_required
def uploadProductsView(request):
    user = request.user
    if user.profile.corporate is True:
        if request.method == 'POST':
            form = DocumentForm(request.POST, request.FILES)
            if form.is_valid():
                # store the uploaded file
                csvfile = request.FILES['document']
                # black magic to detect .csv dialect
                dialect = csv.Sniffer().sniff(codecs.EncodedFile(csvfile, "utf-8").read(1024))
                csvfile.open()
                # get the content from uploaded .csv
                csvcontent = csv.reader(codecs.EncodedFile(csvfile, "utf-8"), delimiter=str(u';'), dialect=dialect)
                # create a new product for every entry (row) in the .csv
                for row in csvcontent:
                    newProduct = Product(user=user,
                                         name=row[0],
                                         p_id=row[1],
                                         p_type=row[2],
                                         price=row[3],
                                         currency=row[4],
                                         date = datetime.date.today(),
                                         time = datetime.datetime.now().strftime('%H:%M:%S'))
                    newProduct.save()
                context_dict={'form': form}
                return redirect('/products/')
        else:
            form = DocumentForm()
        context_dict = {'form':form}
        return render(request, 'corporate/corporate-upload-products.html', context_dict)
    else:
        return redirect('/')


@login_required
def corporateDataView(request):
    user = request.user
    if user.profile.corporate is True:
        # get a list of all categories (returns a list of tuples)
        categories = PurchasedItem.objects.filter(seller=user).order_by().values_list('p_type').distinct()
        # get the actual categories from the tuples
        categories_string = [x[0] for x in categories]
        # save categories and render html
        categories_string.insert(0, 'All')
        context_dict = {'categories': categories_string}
        return render(request, 'corporate/corporate-data.html', context_dict)
    else:
        return redirect('/')

@login_required
def corporateCampaignView(request):
    user = request.user
    if user.profile.corporate is True:
        if request.method == 'POST':
            form = CampaignAdd(request.POST)
            if form.is_valid():
                item = CampaignItem(user= user,
                                    product = Product.objects.get(p_id= form.cleaned_data.get('product_id')),
                                    price = form.cleaned_data.get('price'),
                                    text = form.cleaned_data.get('text'),
                                    currency = form.cleaned_data.get('currency'),
                                    date = datetime.date.today(),
                                    time = datetime.datetime.now().strftime('%H:%M:%S'))
                item.save()
                return redirect('/campaign')
        else:
            form = CampaignAdd()
            items = CampaignItem.objects.filter(user= user)
            context_dict={'form': form, 'items': items}
            return render(request, 'corporate/corporate-campaign.html', context_dict)
    else:
        return redirect ('/')

# MONITOR VIEWS

@login_required
def monthlyStatsView(request):
    user = request.user
    c = converter.CurrencyRates()
    if user.profile.corporate is False:
        # get a list of all categories (returns a list of tuples)
        categories = Product.objects.order_by().values_list('p_type').distinct()
        # get the actual categories from the tuples
        categories_string = [x[0] for x in categories]
        # create two total dicts: one for user, one for rests of users - initialize them
        total = {}
        total_global = {}
        for category in categories_string:
            total[str(category)] = 0
            total_global[str(category)] = 0
        # get today's date and the beginning of the month as datetime objects
        today = datetime.date.today()
        first_of_month = datetime.date(today.year, today.month, 1)
        # get all objects purchased by the user
        PurchaseList = PurchasedItem.objects.filter(user=user)
        # not the best algorithm for finding producs bought last month:
        for item in PurchaseList:
            if item.date >= first_of_month:
                # get rate - could be done before for optimization
                rate = c.get_rate(str(item.currency), 'EUR')
                # convert price to EUR and add to the total
                total[str(item.p_type)] = total[str(item.p_type)] + decimal.Decimal(rate) * item.price
        # do the same for all objects purchased by all other users
        GlobalList = PurchasedItem.objects.all().exclude(user=user)
        for item in GlobalList:
            if item.date >= first_of_month:
                rate = c.get_rate(str(item.currency), 'EUR')
                total_global[str(item.p_type)] = total_global[str(item.p_type)] + decimal.Decimal(rate) * item.price
        # save final totals in a dict and render html
        FinalTotal = {'total': total, 'total_global': total_global}
        return render (request, 'users/monitor/monitor-home.html', FinalTotal)
    else:
        return redirect ('/')



def exploreView(request):
    user=request.user
    if user.profile.corporate is False:
        if request.method == 'POST':
            form = addPost(request.POST)
            if form.is_valid():
                text = form.cleaned_data.get('text')
                newpost = Post(user=user,
                               text=text,
                               date = datetime.date.today(),
                               time = datetime.datetime.now().strftime('%H:%M:%S'))
                newpost.save()
            return redirect('/explore/')
        else:
            # save date and time of last refresh for the user - used when checking for new posts
            request.session['explore_last_time'] = datetime.datetime.now().strftime('%H:%M:%S')
            request.session['explore_last_date'] = str(datetime.date.today())
            form = addPost()
            # get a list of all Friendship objects created by the user (same as accepted)
            userfriends = Friendship.objects.filter(creator = user)
            # get a list of all User objects in the friendship list (friends of logged in user)
            friendlist = [x.friend for x in userfriends]
            # add logged in user to the list so he can see his own posts
            friendlist.append(user)
            # get all posts by Users in friend list
            posts = Post.objects.filter(user__in = friendlist).order_by('id')
            purchased_items = PurchasedItem.objects.filter(user=user)
            ad_companies = []
            ad_types = []
            for item in purchased_items:
                ad_companies.append(item.seller)
                ad_types.append(item.p_type)
            product_query = Product.objects.filter(p_type__in = ad_types )
            ads = CampaignItem.objects.filter(user__in = ad_companies, product__in = product_query)
            context_dict={'form': form, 'posts': posts, 'ads': ads}
            return render(request, 'users/explore/explore-home.html', context_dict)
    else:
        return redirect('/')

### AJAX VIEWS ###

def get_company_data_AJAX(request):
    if request.is_ajax():
        user=request.user
        c = converter.CurrencyRates()
        category = request.GET.get('category')
        if category == "All":
            product_list=PurchasedItem.objects.filter(seller=user)
            total = {}
            total_EUR = 0
            total_per_currency = {'EUR': 0, 'USD': 0, 'RON': 0}

            # get a list of all categories (returns a list of tuples)
            categories = PurchasedItem.objects.filter(seller=user).order_by().values_list('p_type').distinct()
            # get the actual categories from the tuples
            categories_string = [x[0] for x in categories]
            for cat_item in categories_string:
                total[str(cat_item)] = 0
            # get today's date and the beginning of the month as datetime objects
            today = datetime.date.today()
            first_of_month = datetime.date(today.year, today.month, 1)
            for item in product_list:
                if item.date >= first_of_month:
                    # per category
                    # get rate - could be done before for optimization
                    rate = c.get_rate(str(item.currency), 'EUR')
                    # convert price to EUR and add to the total
                    total[str(item.p_type)] = total[str(item.p_type)] + decimal.Decimal(rate) * item.price

                    # per currency
                    total_per_currency[str(item.currency)] = total_per_currency[str(item.currency)] + decimal.Decimal(rate) * item.price
            # total revenue in EUR
            for key, value in total.items():
                total_EUR = total_EUR + value

            context_dict = {'total': total, 'product_list': product_list, 'category': category, 'total_per_currency': total_per_currency, 'total_EUR': total_EUR}
            return render(request, 'ajax/get_company_data.html', context_dict)

        else:
            product_list = PurchasedItem.objects.filter(seller=user, p_type=category)
            total_per_currency = {'EUR': 0, 'USD': 0, 'RON': 0}
            total_EUR = 0
            today = datetime.date.today()
            first_of_month = datetime.date(today.year, today.month, 1)
            top_list = {}
            for item in product_list:
                if item.date < first_of_month:
                    product_list = product_list.exclude(item)
            # get totals per currency
            for item in product_list:
                total_per_currency[item.currency] = total_per_currency[item.currency] + item.price
                rate = c.get_rate(str(item.currency), 'EUR')
                # convert price to EUR and add to the total
                total_EUR = total_EUR + decimal.Decimal(rate) * item.price
            total_EUR = decimal.Decimal(total_EUR).quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
            id_list = product_list.values('dj_id').annotate(dj_count=Count('dj_id'))
            top = id_list.order_by('-dj_count')[:5] # top 5 most sold ids
            for item in top:
                name = Product.objects.get(id = item['dj_id']).name
                top_list[name] = item['dj_count']
            top_objects = Product.objects.filter(id__in = [item['dj_id'] for item in top]).distinct()
            context_dict={'category': category, 'product_list': product_list, 'top_objects': top_objects, 'top_list': top_list, 'total_per_currency': total_per_currency, 'total_EUR': total_EUR}
            return render(request, 'ajax/get_company_data.html', context_dict)
    else:
        return redirect('/')

def get_posts_AJAX(request):
    if request.is_ajax():
        user=request.user
        userfriends = Friendship.objects.filter(creator = user)
        friendlist = [x.friend for x in userfriends]
        posts = Post.objects.filter(user__in = friendlist).order_by('id')
        new = False
        time = request.session['explore_last_time']
        date = request.session['explore_last_date']
        date_obj = datetime.datetime.strptime(date,'%Y-%m-%d').date()
        time_obj = datetime.datetime.strptime(time, '%H:%M:%S').time()
        for post in posts:
            if post.time > time_obj and post.date>=date_obj:
                new = True
                time2=post.time
        context_dict = {'new': new}
        return render(request, 'ajax/get_posts.html', context_dict)
    else:
        return redirect('/')

def send_message_AJAX(request):
    if request.is_ajax():
        if request.method == 'POST':
            message_text = request.POST.get('the_message')
            user2=request.POST.get('user2')
            response_data = {}
            message = Message(message=message_text,
                              user_from=request.user,
                              user_to=User.objects.get(username=user2))
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
    else:
        return redirect('/')

def get_messages_AJAX(request):
    if request.is_ajax():
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
    else:
        return redirect('/')

def get_notifications_AJAX(request):
    if request.is_ajax():
        user = request.user
        notifications = Notification.objects.filter(user = user)
        return render(request, 'ajax/get_notifications.html', {'notifications': notifications})
    else:
        return redirect ('/')

def get_notifications_length_AJAX(request):
    if request.is_ajax():
        user = request.user
        notifications = Notification.objects.filter(user = user, status='unseen')
        return render(request, 'ajax/notiflength.html', {'notifications': notifications})
    else:
        return redirect ('/')

def get_messages_length_AJAX(request):
    if request.is_ajax():
        user = request.user
        messages = Message.objects.filter(user_to=user, status='sending')
        return render(request, 'ajax/messlength.html', {'messages': messages})
    else:
        return redirect ('/')


def mark_as_read_AJAX(request):
    if request.is_ajax():
        user = request.user
        notifications = Notification.objects.filter(user = user, status='unseen')
        for notification in notifications:
            notification.status='seen'
            notification.save()
    else:
        return redirect ('/')
