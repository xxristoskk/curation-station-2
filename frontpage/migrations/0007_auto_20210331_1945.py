# Generated by Django 3.1.6 on 2021-03-31 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontpage', '0006_auto_20210331_0322'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='token_exp',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]