# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-02-06 01:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0004_auto_20180206_0128'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='EUR',
            field=models.IntegerField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='USD',
            field=models.IntegerField(blank=True, max_length=30, null=True),
        ),
    ]
