# Generated by Django 3.2 on 2021-04-29 09:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0003_station_direction'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='station',
            name='direction',
        ),
        migrations.RemoveField(
            model_name='station',
            name='lines',
        ),
        migrations.RemoveField(
            model_name='station',
            name='station_ids',
        ),
        migrations.RemoveField(
            model_name='station',
            name='station_type',
        ),
    ]
