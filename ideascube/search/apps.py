from django.apps import AppConfig
from django.db.models.signals import post_migrate

from .utils import reindex_content


def create_index(sender, **kwargs):
    if isinstance(sender, SearchConfig):
        reindex_content(force=True)


class SearchConfig(AppConfig):
    name = 'ideascube.search'
    verbose_name = 'Search'

    def ready(self):
        post_migrate.connect(create_index, sender=self)
