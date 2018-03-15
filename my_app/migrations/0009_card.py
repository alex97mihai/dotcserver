# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-15 18:27
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('my_app', '0008_auto_20180315_1618'),
    ]

    operations = [
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=15)),
                ('csv', models.CharField(blank=True, max_length=3)),
                ('exp_date', models.DateField(blank=True, null=True)),
                ('name', models.CharField(blank=True, max_length=50)),
                ('address', models.TextField(blank=True)),
                ('phone', models.CharField(max_length=15)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='card_set', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
