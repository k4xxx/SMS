# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-05-16 10:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0004_auto_20180516_1729'),
        ('crm', '0002_customerdistrbute'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userinfo',
            name='password',
        ),
        migrations.RemoveField(
            model_name='userinfo',
            name='username',
        ),
        migrations.AddField(
            model_name='userinfo',
            name='userDetail',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='rbac.User'),
        ),
    ]