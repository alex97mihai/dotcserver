#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# Models below

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='documents', default='media/avatar.jpg')
    USD = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    EUR = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    RON = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    default_payment = models.IntegerField(default = 0, blank=True)
@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class Card(models.Model):
    user = models.ForeignKey(User, related_name="card_set")
    number = models.CharField(max_length=15, blank=True)
    csv = models.CharField(max_length=3, blank=True)
    exp_date = models.CharField(max_length=5, null=True, blank=True)
    name = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15)
    provider = models.CharField(max_length=20, blank=True)


class Friendship(models.Model):
    creator = models.ForeignKey(User, related_name="friendship_creator_set")
    friend = models.ForeignKey(User, related_name="friend_set")
    status = models.CharField(max_length=30, blank=True, default='sent')


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
    target_backup = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    home_backup = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)


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

class Notification(models.Model):
    user = models.ForeignKey(User, related_name="notification_set")
    notification = models.CharField(max_length=30, blank=True)
    notification_type = models.CharField(max_length=30, blank=True, null=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    user2 = models.ForeignKey(User, related_name="notification_friend", blank=True, null=True)
    status = models.CharField(max_length=30, default="unseen")
