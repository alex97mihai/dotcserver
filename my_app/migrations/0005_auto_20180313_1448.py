# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-13 14:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0004_profile_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(default='/static/avatar.jpg', upload_to=b''),
        ),
    ]