# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-17 19:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0011_auto_20180317_1844'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='provider',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
