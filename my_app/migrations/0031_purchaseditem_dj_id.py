# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-04-07 21:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0030_purchaseditem_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseditem',
            name='dj_id',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
