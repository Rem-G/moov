# Generated by Django 3.2 on 2021-05-01 09:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0004_auto_20210429_0900'),
    ]

    operations = [
        migrations.AddField(
            model_name='station',
            name='lat',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='station',
            name='lon',
            field=models.FloatField(null=True),
        ),
    ]
