# Generated by Django 2.2.16 on 2021-02-25 07:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_baselayer_order'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='baselayer',
            options={'ordering': ('order',), 'verbose_name': 'Base Layer', 'verbose_name_plural': 'Base Layers'},
        ),
    ]
