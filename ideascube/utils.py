import sys

from django.conf import locale, settings


class classproperty(property):
    """
    Use it to decorate a classmethod to make it a "class property".
    """
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


def get_all_languages():
    languages = []

    for language, lang_data in locale.LANG_INFO.items():
        try:
            languages.append(
                (language, lang_data['name_local'].capitalize())
            )

        except KeyError:
            # That language doesn't have a local name, only a fallback
            continue

    return sorted(languages)


def get_local_languages():
    # Import here to avoid cyclic import
    from ideascube.models import Setting

    default = _get_used_languages()

    if not default:
        default = ['ar', 'en', 'es', 'fr']

    return Setting.get_list('content', 'local-languages', default=default)


def get_server_name():
    # Import here to avoid cyclic import
    from ideascube.models import Setting

    # This used to be a setting. Keep honoring it for now, so we don't break
    # expectations from users of already deployed boxes.
    default = getattr(settings, 'IDEASCUBE_NAME', 'Ideas Cube')

    return Setting.get_string('server', 'site-name', default=default)


def _get_used_languages():
    # Import here to avoid cyclic import
    from ideascube.blog.models import Content
    from ideascube.library.models import Book
    from ideascube.mediacenter.models import Document

    langs = set()

    for model in (Content, Book, Document):
        for obj in model.objects.all():
            langs.add(obj.lang)

    return sorted(langs)


# We do not use functool.partial cause we want to mock stderr for unittest
# If we use partial we keep a ref to the original sys.stderr and output is not
# captured.
def printerr(*args, **kwargs):
    kwargs['file'] = sys.stderr
    kwargs['flush'] = True
    return print(*args, **kwargs)
