# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-13 15:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0006_auto_20180313_1456'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(default='media/avatar.jpg', upload_to='documents'),
        ),
    ]
