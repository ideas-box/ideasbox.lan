# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-27 10:39
from __future__ import unicode_literals

from django.db import migrations, models
import itertools

def ensure_serial_is_unique(apps, schema_editor):
    Specimen = apps.get_model('monitoring', 'Specimen')
    db_alias = schema_editor.connection.alias

    specimens = Specimen.objects.using(db_alias).order_by('serial')
    grouped_specimens = itertools.groupby(specimens, lambda specimen: specimen.serial)
    for serial, specimens in grouped_specimens:
        specimens = list(specimens)
        if len(specimens) == 1:
            # serial is unique
            continue

        if serial is None:
            # empty (blank) serial. Ignore it.
            continue

        for index, specimen in enumerate(specimens):
            if serial == '':
                specimen.serial = None

            else:
                specimen.serial = "{}~{}".format(serial, index)

            specimen.save()


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0005_auto_20161027_0801'),
    ]

    operations = [
        migrations.RunPython(ensure_serial_is_unique, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='specimen',
            name='serial',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Serial number'),
        ),
    ]
