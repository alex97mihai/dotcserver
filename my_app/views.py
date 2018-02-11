# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from my_app.forms import SignUpForm, TopUpForm, WithdrawForm

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
            
            user.profile.USD = user.profile.USD + form.cleaned_data.get('USD')
            user.save()
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
            
            user.profile.USD = user.profile.USD - form.cleaned_data.get('USD')
            user.save()
            user.profile.EUR = user.profile.EUR - form.cleaned_data.get('EUR')
            user.save()
            return redirect('/hello/')
    else:
        form = WithdrawForm()
    return render(request, 'withdraw.html', {'form': form})
