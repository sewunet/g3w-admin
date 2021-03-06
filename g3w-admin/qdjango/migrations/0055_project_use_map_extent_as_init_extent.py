# Generated by Django 2.2.16 on 2020-10-30 13:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0054_project_context_base_legend'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='use_map_extent_as_init_extent',
            field=models.BooleanField(default=False, verbose_name='User QGIS project map start extent as webgis init extent'),
        ),
    ]
