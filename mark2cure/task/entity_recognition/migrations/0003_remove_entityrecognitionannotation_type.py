# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-11-30 18:05
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('entity_recognition', '0002_entityrecognitionannotation_type_idx'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='entityrecognitionannotation',
            name='type',
        ),
    ]