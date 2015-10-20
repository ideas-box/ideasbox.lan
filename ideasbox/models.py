from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField

from ideasbox.search.models import SearchMixin, SearchableQuerySet

from .fields import CommaSeparatedCharField
from .utils import classproperty


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-
    updating ``created_at`` and ``modified_at`` fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-modified_at", ]


class UserQuerySet(SearchableQuerySet, models.QuerySet):
    pass


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):

    def create_user(self, serial, password=None, **extra):
        if not serial:
            raise ValueError('Users must have a serial')

        user = self.model(serial=serial, **extra)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, serial, password, **extra):
        user = self.create_user(serial=serial, password=password, **extra)
        user.is_staff = True
        user.save(using=self._db)
        return user


class IDBUser(SearchMixin, TimeStampedModel, AbstractBaseUser):
    """
    Minimum definition of a user. Inherit at least from this model.
    """
    USERNAME_FIELD = 'serial'

    LANG_KNOWLEDGE_CHOICES = (
        ('u', _('Understood')),
        ('w', _('Written')),
        ('s', _('Spoken')),
        ('r', _('Read')),
    )

    serial = models.CharField(max_length=40, unique=True)
    short_name = models.CharField(_('usual name'), max_length=30, blank=True)
    full_name = models.CharField(_('full name'), max_length=100, blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user '
                                               'can log into this admin '
                                               'site.'))

    objects = UserManager()

    class Meta:
        ordering = ["-modified_at"]

    def __unicode__(self):
        return self.get_full_name() or self.serial

    def get_absolute_url(self):
        return reverse('user_detail', kwargs={'pk': self.pk})

    def get_full_name(self):
        return self.full_name or self.get_short_name()

    def get_short_name(self):
        return self.short_name

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @classmethod
    def get_data_fields(cls):
        names = ['created_at']
        names.extend(settings.USER_DATA_FIELDS)
        fields = [cls._meta.get_field_by_name(name)[0] for name in names]
        return fields

    @property
    def data_fields(self):
        """Return user public fields labels and values."""
        fields = self.get_data_fields()

        def val(name):
            try:
                return getattr(self, 'get_{0}_display'.format(name))()
            except AttributeError:
                return getattr(self, name)

        out = OrderedDict()
        for f in fields:
            out[f.name] = {'label': f.verbose_name, 'value': val(f.name)}
        return out

    @classproperty
    @classmethod
    def REQUIRED_FIELDS(cls):
        """
        Make it dynamic, as we need to be able to run createsuperuser command
        with every user model.
        """
        already_included = ['serial', 'password']

        def wanted(field):
            return not any([field.blank, field.name in already_included,
                           field.has_default()])

        return [f.name for f in cls._meta.fields if wanted(f)]

    @property
    def index_strings(self):
        return (unicode(getattr(self, name, ''))
                for name in settings.USER_INDEX_FIELDS)

    index_public = False  # Searchable only by staff.

    OCCUPATION_CHOICES = (
        ('student', _('Student')),
        ('teacher', _('Teacher')),
        ('no_profession', _('Without profession')),
        ('profit_profession', _('Profit profession')),
        ('other', _('Other')),
    )

    FAMILY_STATUS_CHOICES = (
        ('with_family', _('Lives with family in {place}').format(
            place=settings.IDEASBOX_PLACE_NAME)),
        ('no_family', _('Lives without family in {place}').format(
            place=settings.IDEASBOX_PLACE_NAME)),
        ('without_family', _('Has family in {place} but lives without').format(
            place=settings.IDEASBOX_PLACE_NAME)),
    )

    CAMP_ACTIVITY_CHOICES = (
        ('1', _('Comitees, representation groups')),
        ('2', _('Music, dance, singing')),
        ('3', _('Other cultural activities')),
        ('4', _('Informatic workshops')),
        ('5', _('Literacy working group')),
        ('6', _('Talking group')),
        ('7', _('Recreational')),
        ('8', _('Volunteering')),
        ('9', _('Psycosocial')),
        ('10', _('Educational')),
        ('11', _('Sport')),
    )

    BOX_AWARENESS_CHOICES = (
        ('seen_box', _('Seen the Box')),
        ('partner', _('Has been informed by partner organization')),
        ('other_org', _('Has been informed by other organization')),
        ('word_of_mouth', _('Word of mouth')),
        ('campaign', _('Poster campaign')),
        ('other', _('Other')),
    )

    SCHOOL_LEVEL_CHOICES = (
        ('primary', _('Primary')),
        ('secondary', _('Secondary')),
        ('professional', _('Professional')),
        ('college', _('Higher education')),
    )

    MARITAL_STATUS_CHOICES = (
        ('couple', _('Couple')),
        ('single', _('Single')),
        ('widowed', _('Widowed')),
    )

    GENDER_CHOICES = (
        ('undefined', _('Undefined')),
        ('male', _('Male')),
        ('female', _('Female')),
    )

    latin_name = models.CharField(_('Latin written name'),
                                  max_length=200, blank=True)

    birth_year = models.PositiveSmallIntegerField(
        _('Birth year'), blank=True, null=True)
    gender = models.CharField(
        _('Gender'), choices=GENDER_CHOICES, blank=True,
        max_length=32)
    country = CountryField(_('Country of origin'), max_length=100, blank=True)
    city = models.CharField(_('City of origin'), max_length=100, blank=True)
    id_card_number = models.CharField(_('ID card number'), max_length=50,
                                      blank=True)
    children_under_12 = models.PositiveSmallIntegerField(
        _('Number of children under 12'),
        blank=True, null=True)
    children_under_18 = models.PositiveSmallIntegerField(
        _('Number of children under 18'),
        blank=True, null=True)
    children_above_18 = models.PositiveSmallIntegerField(
        _('Number of children above 18'),
        blank=True, null=True)
    school_level = models.CharField(
        _('School level'), choices=SCHOOL_LEVEL_CHOICES, blank=True,
        max_length=32)
    marital_status = models.CharField(
        _('Marital situation'), choices=MARITAL_STATUS_CHOICES, blank=True,
        max_length=32)
    box_awareness = models.CharField(
        _('Ideas Box awareness'), choices=BOX_AWARENESS_CHOICES, blank=True,
        max_length=32)

    refugee_id = models.CharField(_('Refugee ID'), max_length=100, blank=True)
    camp_entry_date = models.DateField(_('Camp entry date'), blank=True,
                                       null=True)
    current_occupation = models.CharField(
        _('Current occupation'), choices=OCCUPATION_CHOICES, blank=True,
        max_length=32)
    country_of_origin_occupation = models.CharField(
        _('Occupation in the country of origin'),
        max_length=100,
        blank=True)
    family_status = models.CharField(
        _('Family status'), choices=FAMILY_STATUS_CHOICES, blank=True,
        max_length=32)
    is_sent_to_school = models.BooleanField(
        _('Sent to school in the country of origin (if under 18)'),
        default=False)
    camp_activities = CommaSeparatedCharField(
        _('Activities in the camp'),
        max_length=512,
        choices=CAMP_ACTIVITY_CHOICES,
        blank=True)
    camp_address = models.CharField(_('Address in the camp'),
                                    max_length=200, blank=True)

    en_level = CommaSeparatedCharField(
        _('English knowledge'), choices=LANG_KNOWLEDGE_CHOICES,
        blank=True, max_length=32)
    ar_level = CommaSeparatedCharField(
        _('Arabic knowledge'), choices=LANG_KNOWLEDGE_CHOICES,
        blank=True, max_length=32)
    rn_level = CommaSeparatedCharField(
        _('Kirundi knowledge'), choices=LANG_KNOWLEDGE_CHOICES,
        blank=True, max_length=32)
    fr_level = CommaSeparatedCharField(
        _('French knowledge'), choices=LANG_KNOWLEDGE_CHOICES,
        blank=True, max_length=32)
    sw_level = CommaSeparatedCharField(
        _('Swahili knowledge'), choices=LANG_KNOWLEDGE_CHOICES,
        blank=True, max_length=32)
