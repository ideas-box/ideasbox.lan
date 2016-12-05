# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-28 16:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0010_section_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='section',
            field=models.CharField(choices=[('digital', 'digital'), ('children-cartoons', 'children - cartoons'), ('children-novels', 'children - novels'), ('children-poetry', 'children - poetry'), ('children-theatre', 'children - theatre'), ('children-documentary', 'children - documentary'), ('children-comics', 'children - comics'), ('children-tales', 'children - tales'), ('children-myths', 'chirdren - myths and legends'), ('adults-novels', 'adults - novels'), ('adults-poetry', 'adults - poetry'), ('adults-theatre', 'adults - theatre'), ('adults-documentary', 'adults - documentary'), ('adults-comics', 'adults - comics'), ('adults-tales', 'adults - tales'), ('adults-myths', 'adults - myths and legends'), ('game', 'game'), ('OTHER', 'other')], default='OTHER', max_length=50, verbose_name='section'),
        ),
    ]
