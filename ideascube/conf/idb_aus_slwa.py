# -*- coding: utf-8 -*-
"""State Library Western Australia box"""
from .idb import *  # noqa
from django.utils.translation import ugettext_lazy as _

#IDEASCUBE_NAME = u"State Library Western Australia"
IDEASCUBE_PLACE_NAME = _("the community")
COUNTRIES_FIRST = ['AU']
TIME_ZONE = 'Australia/Darwin'
LANGUAGE_CODE = 'en'
LOAN_DURATION = 14
MONITORING_ENTRY_EXPORT_FIELDS = ['serial', 'user_id', 'birth_year', 'gender']
USER_FORM_FIELDS = (
    ('Ideasbox', ['serial', 'box_awareness']),
    (_('Personal informations'), ['short_name', 'full_name', 'birth_year', 'gender', 'id_card_number']),  # noqa
    (_('Family'), ['marital_status', 'family_status', 'children_under_12', 'children_under_18', 'children_above_18']),  # noqa
    (_('In the town'), ['current_occupation', 'school_level']),
    (_('Language skills'), ['en_level']),
)

HOME_CARDS = STAFF_HOME_CARDS + [
    {
        'id': 'blog',
    },
    {
        'id': 'mediacenter',
    },
    {
        'id': 'library',
    },
    {
        'id': 'wikipedia',
        'languages': ['en']
    },
    {
        'id': 'khanacademy',
    },
    {
        'id': 'gutenberg',
        'lang': 'en',
    },
    {
        'id': 'vikidia',
        'languages': ['en']
    },
]
