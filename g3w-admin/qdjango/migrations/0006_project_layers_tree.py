# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-16 10:44


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0005_auto_20160315_0844'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='layers_tree',
            field=models.TextField(blank=True, null=True, verbose_name='Layers tree structure'),
        ),
    ]
