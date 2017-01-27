# -*- coding: utf-8 -*-
import os
import argparse
import glob

from django.conf import settings
from django.core.management.base import BaseCommand

from ideascube.mediacenter.models import Document
from ideascube.utils import printerr


class Command(BaseCommand):
    help = 'Remove files from the mediacenter.'

    def add_arguments(self, parser):
        subs = parser.add_subparsers(
            title='Commands', dest='cmd', metavar='',
            parser_class=argparse.ArgumentParser)
        clean_leftover = subs.add_parser(
            'leftover-files',
            help='Clean mediacenter files not associated with a document.')
        clean_leftover.set_defaults(func=self.clean_leftover)
        parser.add_argument('--dry-run', action='store_true',
                            help='Print the list of medias that would be '
                                 'removed. Do not actually remove them')

    def handle(self, *args, **options):
        if 'func' not in options:
            self.parser.print_help()
            self.parser.exit(1)

        options['func'](options)

    def clean_leftover(self, options):
        files_to_remove = self._get_leftover_files()
        if options['dry_run']:
            print("Files to remove are :")
            for _file in files_to_remove:
                print(" - '{}'".format(_file))
        else:
            for f in files_to_remove:
                try:
                    os.unlink(f)
                except Exception as e:
                    printerr("ERROR while deleting {}".format(f))
                    printerr("Exception is {}".format(e))

    def _get_leftover_files(self):
        # List all (original and preview) files in the fs
        original_files_root_dir = os.path.join(settings.MEDIA_ROOT,
                                               'mediacenter/document')
        files_in_fs = set(
            glob.iglob(os.path.join(original_files_root_dir, '*')))

        preview_files_root_dir = os.path.join(settings.MEDIA_ROOT,
                                    'mediacenter/preview')
        files_in_fs.update(
            glob.iglob(os.path.join(preview_files_root_dir, '*')))

        # Remove known original paths.
        original_pathes = Document.objects.all().values_list(
            'original', flat=True)
        original_pathes = (os.path.join(settings.MEDIA_ROOT, path)
                           for path in original_pathes)
        files_in_fs.difference_update(original_pathes)

        # Remove known preview paths.
        preview_pathes = Document.objects.all().values_list(
            'preview', flat=True)
        preview_pathes = (os.path.join(settings.MEDIA_ROOT, path)
                          for path in preview_pathes if path)
        files_in_fs.difference_update(preview_pathes)

        return files_in_fs
