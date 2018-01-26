from django.forms import widgets

from ideascube.configuration import get_config
from django.utils.html import mark_safe, escape
from django.utils.encoding import force_text
from django.forms.utils import flatatt
from django.utils.translation import get_language

from .utils import clean_html


_ideascube_to_tinyMCE_language_map = {
    'fr': 'fr_FR'
}


class RichTextEntry(widgets.Widget):
    def __init__(self, *, with_media=False, attrs=None):
        super().__init__(attrs=attrs)
        self.with_media = with_media

    def get_language(self):
        ideascube_language = get_language()
        return _ideascube_to_tinyMCE_language_map.get(
            ideascube_language, ideascube_language)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''

        if attrs is None:
            attrs = {}

        # The widget displayed to the user
        div_attrs = {'id': name,
                     'class': 'tinymce-editor',
                     'data-tinymce-use-media': self.with_media,
                     'data-tinymce-language-code': self.get_language()
                    }
        div_html = '<div{}>{}</div>'.format(
            flatatt(div_attrs),
            force_text(value)
        )

        # The input used by django
        attrs.update({'name': name, 'value': escape(value), 'type': 'hidden'})

        input_attrs = self.build_attrs(attrs)
        input_html = '<input{} />'.format(
            flatatt(input_attrs)
        )

        html = '\n'.join([div_html, input_html])
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        raw_html_input = super().value_from_datadict(data, files, name)
        filtered_html = clean_html(raw_html_input, with_media=self.with_media)

        return filtered_html


class LangSelect(widgets.Select):
    option_template_name = 'ideascube/includes/widgets/langselect_option.html'

    def optgroups(self, name, value, attrs=None):
        optgroups = super().optgroups(name, value, attrs=attrs)
        local_languages = get_config('content', 'local-languages')

        if local_languages is None:
            return optgroups

        result = []

        for group_name, group_choices, group_index in optgroups:
            choices = []

            for option in group_choices:
                if option['value'] == '':
                    choices.append(option)

                elif option['value'] in local_languages:
                    choices.append(option)

                elif option['selected']:
                    choices.append(option)

            result.append((group_name, choices, group_index))

        return result
