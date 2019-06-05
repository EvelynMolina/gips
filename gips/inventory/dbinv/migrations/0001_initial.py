# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-28 18:23
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver', models.TextField(db_index=True)),
                ('asset', models.TextField(db_index=True)),
                ('sensor', models.TextField(db_index=True)),
                ('tile', models.TextField(db_index=True)),
                ('date', models.DateField(db_index=True)),
                ('name', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver', models.TextField(db_index=True)),
                ('product', models.TextField(db_index=True)),
                ('sensor', models.TextField(db_index=True)),
                ('tile', models.TextField(db_index=True)),
                ('date', models.DateField(db_index=True)),
                ('name', models.TextField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='product',
            unique_together=set([('driver', 'product', 'tile', 'date')]),
        ),
        migrations.AlterUniqueTogether(
            name='asset',
            unique_together=set([('driver', 'asset', 'tile', 'date')]),
        ),
    ]
