from datetime import datetime, timezone

import freezegun

import pytest

from ideascube.configuration import get_config, reset_config, set_config
from ideascube.configuration.exceptions import (
    InvalidConfigurationValueError,
    NoSuchConfigurationKeyError,
    NoSuchConfigurationNamespaceError,
)
from ideascube.configuration.models import Configuration


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('value', [
    pytest.param(True, id='boolean'),
    pytest.param(42, id='int'),
    pytest.param('A string', id='string'),
    pytest.param(['A', 'list'], id='list'),
])
def test_get_configuration(monkeypatch, value, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': type(value), 'default': "whatever"}}})

    Configuration(
        namespace='tests', key='setting1', value=value, actor=user).save()

    assert get_config('tests', 'setting1') == value


def test_get_configuration_invalid_namespace(monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(NoSuchConfigurationNamespaceError):
        get_config('tests', 'setting1')


def test_get_configuration_invalid_key(monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'tests': {}})

    with pytest.raises(NoSuchConfigurationKeyError):
        get_config('tests', 'setting1')


def test_get_configuration_invalid_type(capsys, monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': int, 'default': 42}}})

    # Store a bad value in the database
    Configuration(
        namespace='tests', key='setting1', value='foo', actor=user).save()

    assert get_config('tests', 'setting1') == 42

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip().split(':') == [
        'ERROR', 'ideascube.configuration',
        "The stored value for tests.setting1='foo' is of type <class 'str'> "
        "instead of <class 'int'>. This should never have happened."]


def test_get_default_configuration(monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': int, 'default': 42}}})

    assert get_config('tests', 'setting1') == 42


def test_reset_configuration(monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {
            'tests': {
                'setting1': {'type': str},
                'setting2': {'type': int},
            },
            'tests2': {
                'setting3': {'type': list},
            },
        })

    set_config('tests', 'setting1', 'A string', user)
    set_config('tests', 'setting2', 42, user)
    set_config('tests2', 'setting3', ['A', 'list'], user)
    assert Configuration.objects.count() == 3

    reset_config('tests', 'setting1')
    assert Configuration.objects.count() == 2

    with pytest.raises(Configuration.DoesNotExist):
        Configuration.objects.get(namespace='tests', key='settings1')


def test_reset_default_configuration(monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': str}}})

    reset_config('tests', 'setting1')

    assert Configuration.objects.count() == 0


def test_reset_configuration_invalid_type(capsys, monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': int}}})

    # Store a bad value in the database
    Configuration(
        namespace='tests', key='setting1', value='foo', actor=user).save()
    reset_config('tests', 'setting1')

    assert Configuration.objects.count() == 0

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip().split(':') == [
        'ERROR', 'ideascube.configuration',
        "The stored value for tests.setting1='foo' is of type <class 'str'> "
        "instead of <class 'int'>. This should never have happened."]


@pytest.mark.parametrize('value1, value2', [
    pytest.param(True, False, id='boolean'),
    pytest.param(42, 43, id='int'),
    pytest.param('A string', 'Another string', id='string'),
    pytest.param(['A', 'list'], ['Another', 'list'], id='list'),
])
def test_set_configuration(monkeypatch, value1, value2, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': type(value1)}}})

    fakenow = datetime.now(tz=timezone.utc)

    with freezegun.freeze_time(fakenow):
        set_config('tests', 'setting1', value1, user)

    assert Configuration.objects.count() == 1

    configuration = Configuration.objects.first()
    assert configuration.namespace == 'tests'
    assert configuration.key == 'setting1'
    assert configuration.value == value1
    assert configuration.actor == user
    assert configuration.date == fakenow
    assert str(configuration) == 'tests.setting1=%r' % value1

    set_config('tests', 'setting1', value2, user)

    assert Configuration.objects.count() == 1

    configuration = Configuration.objects.first()
    assert configuration.namespace == 'tests'
    assert configuration.key == 'setting1'
    assert configuration.value == value2
    assert str(configuration) == 'tests.setting1=%r' % value2


def test_set_configuration_invalid_namespace(monkeypatch, user):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(NoSuchConfigurationNamespaceError):
        set_config('tests', 'setting1', 'value1', user)


def test_set_configuration_invalid_key(monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'tests': {}})

    with pytest.raises(NoSuchConfigurationKeyError):
        set_config('tests', 'setting1', 'value1', user)


def test_set_configuration_invalid_type(monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'tests': {'setting1': {'type': int}}})

    with pytest.raises(InvalidConfigurationValueError):
        set_config('tests', 'setting1', 'value1', user)
