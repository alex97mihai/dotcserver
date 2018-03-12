# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-12 17:18
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CompleteOrders',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.CharField(blank=True, max_length=30)),
                ('date', models.DateField(blank=True, null=True)),
                ('time', models.TimeField(blank=True, null=True)),
                ('home_currency', models.CharField(blank=True, max_length=30)),
                ('home_currency_amount', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('rate', models.DecimalField(decimal_places=3, max_digits=10)),
                ('target_currency', models.CharField(blank=True, max_length=30)),
                ('target_currency_amount', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('status', models.CharField(blank=True, default='complete', max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Friendship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(blank=True, default='sent', max_length=30)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendship_creator_set', to=settings.AUTH_USER_MODEL)),
                ('friend', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friend_set', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification', models.CharField(blank=True, max_length=30)),
                ('notification_type', models.CharField(blank=True, max_length=30)),
                ('date', models.DateField(blank=True, null=True)),
                ('time', models.TimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_set', to=settings.AUTH_USER_MODEL)),
                ('user2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notification_friend', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.CharField(blank=True, max_length=30)),
                ('date', models.DateField(blank=True, null=True)),
                ('time', models.TimeField(blank=True, null=True)),
                ('home_currency', models.CharField(blank=True, max_length=30)),
                ('home_currency_amount', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('rate', models.DecimalField(decimal_places=3, max_digits=10)),
                ('target_currency', models.CharField(blank=True, max_length=30)),
                ('target_currency_amount', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('status', models.CharField(blank=True, default='pending', max_length=30)),
                ('target_backup', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
                ('home_backup', models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bio', models.TextField(blank=True, max_length=500)),
                ('location', models.CharField(blank=True, max_length=30)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('USD', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('EUR', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('RON', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
