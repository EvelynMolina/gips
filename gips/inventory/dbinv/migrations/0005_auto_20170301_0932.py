# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-03-01 09:32
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbinv', '0004_auto_20170227_0817'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='result',
            unique_together=set([('job', 'date', 'fid')]),
        ),
    ]
