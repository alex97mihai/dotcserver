#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.


from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    USD = models.IntegerField(max_length=30, blank=True, null=True, default=0)
    EUR = models.IntegerField(max_length=30, blank=True, null=True, default=0)
@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class Order(models.Model):
    user = models.CharField(max_length=30, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    home_currency = models.CharField(max_length=30, blank=True)
    home_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=3)
    target_currency = models.CharField(max_length=30, blank=True)
    target_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, default='pending')

class CompleteOrders(models.Model):   
    user = models.CharField(max_length=30, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    home_currency = models.CharField(max_length=30, blank=True)
    home_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=3)
    target_currency = models.CharField(max_length=30, blank=True)
    target_currency_amount = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    status = models.CharField(max_length=30, blank=True, default='complete')
 

