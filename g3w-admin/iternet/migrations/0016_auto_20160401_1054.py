# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-01 10:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iternet', '0015_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='config',
            name='qdjango_project',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='qdjango.Project'),
            preserve_default=False,
        ),
    ]
