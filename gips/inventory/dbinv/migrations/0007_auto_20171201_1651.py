# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-12-01 16:51
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbinv', '0006_auto_20170508_2002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Geometry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('driver', models.TextField()),
                ('wkt', django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='geometry',
            unique_together=set([('driver', 'name')]),
        ),
    ]
