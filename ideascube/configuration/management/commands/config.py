import argparse

from django.core.management.base import BaseCommand, CommandError

from ideascube.configuration import get_config
from ideascube.configuration.exceptions import (
    NoSuchConfigurationKeyError,
    NoSuchConfigurationNamespaceError,
    )
from ideascube.configuration.registry import (
    get_all_namespaces, get_namespaced_configs,
    )


class Command(BaseCommand):
    help = 'Manage server configuration'

    def add_arguments(self, parser):
        subs = parser.add_subparsers(
            title='Commands', dest='cmd', metavar='',
            parser_class=argparse.ArgumentParser)

        get = subs.add_parser(
            'get', help='Get the current value of a configuration option')
        get.add_argument('namespace', help='The configuration namespace')
        get.add_argument('key', help='The configuration key')
        get.set_defaults(func=self.get_config)

        list = subs.add_parser(
            'list', help='List configuration namespaces and keys')
        list.add_argument(
            'namespace', nargs='?',
            help='Only list configuration keys for this namespace')
        list.set_defaults(func=self.list_configs)

        self.parser = parser

    def handle(self, *_, **options):
        if 'func' not in options:
            self.parser.print_help()
            self.parser.exit(1)

        options['func'](options)

    def get_config(self, options):
        namespace = options['namespace']
        key = options['key']

        try:
            value = get_config(namespace, key)

        except (NoSuchConfigurationNamespaceError,
                NoSuchConfigurationKeyError) as e:
            raise CommandError(e)

        print('%r' % value)

    def list_configs(self, options):
        namespace = options['namespace']

        if namespace is None:
            for namespace in get_all_namespaces():
                print(namespace)

            return

        try:
            for key in get_namespaced_configs(namespace):
                print("%s %s" % (namespace, key))

        except NoSuchConfigurationNamespaceError as e:
            raise CommandError(e)