# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-16 22:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0009_card'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='default_payment',
            field=models.IntegerField(blank=True, default=0),
        ),
    ]
