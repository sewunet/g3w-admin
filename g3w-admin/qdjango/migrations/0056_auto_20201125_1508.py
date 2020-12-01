# Generated by Django 2.2.16 on 2020-11-25 15:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('qdjango', '0055_project_use_map_extent_as_init_extent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qdjango_project', to='core.Group', verbose_name='Group'),
        ),
    ]