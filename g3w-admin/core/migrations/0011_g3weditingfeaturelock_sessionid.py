# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-18 10:29


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_auto_20160406_0813'),
    ]

    operations = [
        migrations.AddField(
            model_name='g3weditingfeaturelock',
            name='sessionid',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
