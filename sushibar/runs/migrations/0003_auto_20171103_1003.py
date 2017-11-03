# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-11-03 17:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0002_auto_20170630_1740'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentchannel',
            name='trello_url',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contentchannelrun',
            name='failed',
            field=models.BooleanField(default=False),
        ),
    ]
