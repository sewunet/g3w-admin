# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-10-03 09:23


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0026_auto_20160913_1515'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='wfscapabilities',
            field=models.IntegerField(blank=True, null=True, verbose_name='Bitwise wfs options'),
        ),
    ]
