# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-31 18:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0018_post_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='corporate',
            field=models.BooleanField(default=False),
        ),
    ]
