# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-10-28 09:18


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_macrogroup_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='macrogroup',
            name='groups',
            field=models.ManyToManyField(blank=True, to='core.Group'),
        ),
    ]
