# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-24 04:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbinv', '0002_datahandler'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='sched_id',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='sched_id',
            field=models.TextField(blank=True, null=True),
        ),
    ]