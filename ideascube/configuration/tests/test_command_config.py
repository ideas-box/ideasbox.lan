from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from ideascube.configuration import get_config, set_config
from ideascube.configuration.models import Configuration


@pytest.mark.usefixtures('db')
@pytest.mark.parametrize('value, expected, default', [
    pytest.param(True, 'True', False, id='boolean'),
    pytest.param(42, '42', 0, id='int'),
    pytest.param('A string', "'A string'", 'default', id='string'),
    pytest.param(['A', 'list'], "['A', 'list']", [], id='list'),
])
def test_get_config(capsys, monkeypatch, user, value, expected, default):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': type(value), 'default': default}}})

    set_config('namespace1', 'key1', value, user)
    call_command('config', 'get', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip() == expected
    assert err.strip() == ''


@pytest.mark.usefixtures('db')
def test_get_default_config(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': int, 'default': 0}}})

    call_command('config', 'get', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip() == '0'
    assert err.strip() == ''


def test_get_config_no_namespace(monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'get', 'namespace1', 'key1')

    assert (
        'Unknown configuration namespace: "namespace1"') in str(exc_info.value)


def test_get_config_no_key(monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'namespace1': {}})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'get', 'namespace1', 'key1')

    assert (
        'Unknown configuration key: "namespace1.key1"') in str(exc_info.value)


@pytest.mark.usefixtures('db')
def test_get_invalid_config(capsys, monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': int, 'default': 0}}})

    # Make an invalid config, this should never happen in theory
    Configuration(
        namespace='namespace1', key='key1', value='foo', actor=user).save()

    call_command('config', 'get', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip() == '0'
    assert err.strip().split(':') == [
        'ERROR', 'ideascube.configuration',
        "The stored value for namespace1.key1='foo' is of type <class 'str'> "
        "instead of <class 'int'>. This should never have happened."]


def test_describe_config(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {
            'namespace1': {
                'key1': {
                    'summary': 'A configuration key',
                    'pretty_type': 'A string',
                    'default': 'the default',
                },
            }})

    call_command('config', 'describe', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip().split('\n') == [
        '# namespace1 key1',
        '',
        'A configuration key',
        '',
        '* type: A string',
        "* default value: 'the default'"]
    assert err.strip() == ''


def test_describe_config_no_namespace(monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'describe', 'namespace1', 'key1')

    assert (
        'Unknown configuration namespace: "namespace1"') in str(exc_info.value)


def test_describe_config_no_key(monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'namespace1': {}})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'describe', 'namespace1', 'key1')

    assert (
        'Unknown configuration key: "namespace1.key1"') in str(exc_info.value)


def test_list_namespaces(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace2': {'key2': {}}, 'namespace1': {}})

    call_command('config', 'list')

    out, err = capsys.readouterr()
    assert out.strip().split('\n') == ['namespace1', 'namespace2']
    assert err.strip() == ''


def test_list_no_namespaces(capsys, monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    call_command('config', 'list')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_list_keys(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {}, 'key2': {}}})

    call_command('config', 'list', 'namespace1')

    out, err = capsys.readouterr()
    assert out.strip().split('\n') == ['namespace1 key1', 'namespace1 key2']
    assert err.strip() == ''


def test_list_no_keys(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'namespace1': {}})

    call_command('config', 'list', 'namespace1')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_list_keys_invalid_namespace(capsys, monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'list', 'namespace1')

    assert (
        'Unknown configuration namespace: "namespace1"') in str(exc_info.value)


@pytest.mark.usefixtures('db')
def test_report_config(capsys, monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {}, 'key2': {}}})
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {
            'namespace2': {
                'key1': {'type': list, 'default': []},
            },
            'namespace1': {
                'key2': {'type': int, 'default': 0},
                'key1': {'type': str, 'default': 'default'},
            },
        })

    set_config('namespace1', 'key1', 'value', user)
    set_config('namespace2', 'key1', ['a', 'value'], user)

    call_command('config', 'report')

    out, err = capsys.readouterr()
    assert out.strip().split('\n') == [
        "namespace1 key1: 'value' (default: 'default')",
        "namespace1 key2: 0 (default: 0)",
        "namespace2 key1: ['a', 'value'] (default: [])",
    ]
    assert err == ''


@pytest.mark.usefixtures('db')
def test_reset_config(capsys, monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': str, 'default': 'default'}}})

    set_config('namespace1', 'key1', 'A string', user)
    call_command('config', 'reset', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''

    assert get_config('namespace1', 'key1') == 'default'


@pytest.mark.usefixtures('db')
def test_reset_default_config(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': str, 'default': 'default'}}})

    call_command('config', 'reset', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''

    assert get_config('namespace1', 'key1') == 'default'


def test_reset_invalid_namespace(capsys, monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'reset', 'namespace1', 'key1')

    assert (
        'Unknown configuration namespace: "namespace1"') in str(exc_info.value)


def test_reset_invalid_key(capsys, monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'namespace1': {}})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'reset', 'namespace1', 'key1')

    assert (
        'Unknown configuration key: "namespace1.key1"') in str(exc_info.value)


@pytest.mark.usefixtures('db')
def test_reset_invalid_config(capsys, monkeypatch, user):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': int, 'default': 0}}})

    # Make an invalid config, this should never happen in theory
    Configuration(
        namespace='namespace1', key='key1', value='foo', actor=user).save()

    call_command('config', 'reset', 'namespace1', 'key1')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip().split(':') == [
        'ERROR', 'ideascube.configuration',
        "The stored value for namespace1.key1='foo' is of type <class 'str'> "
        "instead of <class 'int'>. This should never have happened."]

    assert get_config('namespace1', 'key1') == 0

    # No log added this time, the invalid value is gone
    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


@pytest.mark.usefixtures('db', 'systemuser')
@pytest.mark.parametrize('value, expected, type, default', [
    pytest.param("True", True, bool, False, id='boolean'),
    pytest.param("true", True, bool, False, id='boolean-2'),
    pytest.param("42", 42, int, 0, id='int'),
    pytest.param("'A string'", 'A string', str, 'default', id='string'),
    pytest.param("unquoted-string", 'unquoted-string', str, 'default', id='string-2'),
    pytest.param("['A', 'list']", ['A', 'list'], list, [], id='list'),
])
def test_set_config(capsys, monkeypatch, value, expected, type, default):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': type, 'default': default}}})

    call_command('config', 'set', 'namespace1', 'key1', value)

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''

    assert get_config('namespace1', 'key1') == expected


@pytest.mark.usefixtures('db', 'systemuser')
def test_set_config_no_namespace(monkeypatch):
    monkeypatch.setattr('ideascube.configuration.registry.REGISTRY', {})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'set', 'namespace1', 'key1', "'value 1'")

    assert (
        'Unknown configuration namespace: "namespace1"') in str(exc_info.value)


@pytest.mark.usefixtures('db', 'systemuser')
def test_set_config_no_key(monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY', {'namespace1': {}})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'set', 'namespace1', 'key1', "'value 1'")

    assert (
        'Unknown configuration key: "namespace1.key1"') in str(exc_info.value)


@pytest.mark.usefixtures('db', 'systemuser')
def test_set_invalid_config(monkeypatch):
    monkeypatch.setattr(
        'ideascube.configuration.registry.REGISTRY',
        {'namespace1': {'key1': {'type': int, 'default': 0}}})

    with pytest.raises(CommandError) as exc_info:
        call_command('config', 'set', 'namespace1', 'key1', "'value 1'")

    assert (
        'Invalid type for configuration key "namespace1.key1": expected '
        "<class 'int'>, got <class 'str'>") in str(exc_info.value)
