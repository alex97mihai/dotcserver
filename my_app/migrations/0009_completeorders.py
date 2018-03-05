# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-05 14:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0008_auto_20180301_0108'),
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
    ]
