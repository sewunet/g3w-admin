# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-10-03 10:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usersmanage', '0009_auto_20190710_1436'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userbackend',
            name='backend',
            field=models.CharField(choices=[(b'g3wsuite', 'G3WSUITE'), ('ldap', 'LDAP')], default=b'g3wsuite', max_length=255, verbose_name='Backend'),
        ),
    ]
