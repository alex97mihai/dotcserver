# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-04-06 22:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0029_product_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseditem',
            name='url',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
    ]
