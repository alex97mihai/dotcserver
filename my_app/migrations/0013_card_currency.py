# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-17 20:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0012_card_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='currency',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
