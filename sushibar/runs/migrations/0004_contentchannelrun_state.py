# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-11-10 00:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0003_contentchannel_trello_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentchannelrun',
            name='state',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
