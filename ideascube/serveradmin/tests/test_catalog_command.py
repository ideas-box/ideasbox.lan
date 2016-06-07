from operator import itemgetter
import shutil

from django.core.management import call_command
from django.core.management.base import CommandError
import pytest
import yaml


def fake_urlretrieve(url, path, reporthook=None):
    assert url.startswith('file://')

    src = url[7:]
    shutil.copyfile(src, path)


def test_no_command(tmpdir, settings, capsys):
    with pytest.raises(SystemExit):
        call_command('catalog')

    out, err = capsys.readouterr()
    assert out.strip().startswith('usage: ')
    assert err.strip() == ''


def test_add_remote(tmpdir, settings, capsys, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    remote = {
        'id': 'foo', 'name': 'Content from Foo',
        'url': 'file://{}'.format(remote_catalog_file.strpath),
        }
    expected = {
        'id': remote['id'], 'name': remote['name'], 'url': remote['url']}

    call_command(
        'catalog', 'remotes', 'add', remote['id'], remote['name'],
        remote['url'])

    # Ensure the remote has been added
    assert tmpdir.join('remotes').check(dir=True)
    assert tmpdir.join('remotes', 'foo.yml').check(file=True)

    with tmpdir.join('remotes', 'foo.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == expected

    # Ensure the cache has been updated
    assert tmpdir.join('catalog.yml').check(file=True)

    expected = {'installed': {}, 'available': {
        'foovideos': {'name': 'Videos from Foo'},
        }}

    with tmpdir.join('catalog.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == expected

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_cannot_add_duplicate_remote(tmpdir, settings, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    remote = {
        'id': 'foo', 'name': 'Content from Foo',
        'url': 'file://{}'.format(remote_catalog_file.strpath),
        }

    call_command(
        'catalog', 'remotes', 'add', remote['id'], remote['name'],
        remote['url'])

    assert tmpdir.join('remotes').check(dir=True)
    assert tmpdir.join('remotes', 'foo.yml').check(file=True)

    old_mtime = tmpdir.join('remotes', 'foo.yml').mtime()

    # Adding the same remote with the same url should not fail.
    call_command(
        'catalog', 'remotes', 'add', remote['id'], remote['name'],
        remote['url'])

    # But should fail with different urls.
    with pytest.raises(CommandError):
        call_command(
            'catalog', 'remotes', 'add', remote['id'], remote['name'],
            remote['url'] + "bad")

    assert tmpdir.join('remotes', 'foo.yml').mtime() == old_mtime


def test_remove_remote(tmpdir, settings, capsys, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    remote = {
        'id': 'foo', 'name': 'Content from Foo',
        'url': 'file://{}'.format(remote_catalog_file.strpath),
        }

    call_command(
        'catalog', 'remotes', 'add', remote['id'], remote['name'],
        remote['url'])
    call_command('catalog', 'remotes', 'remove', remote['id'])

    # Ensure the remote has been removed
    assert tmpdir.join('remotes').check(dir=True)
    assert tmpdir.join('remotes').listdir() == []

    # Ensure the cache has been updated
    assert tmpdir.join('catalog.yml').check(file=True)

    expected = {'installed': {}, 'available': {}}

    with tmpdir.join('catalog.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == expected

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_cannot_remove_unexisting_remote(tmpdir, settings):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    with pytest.raises(CommandError):
        call_command('catalog', 'remotes', 'remove', 'foo')


def test_list_no_remotes(tmpdir, settings, capsys):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    call_command('catalog', 'remotes', 'list')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_add_then_list_multiple_remotes(tmpdir, settings, capsys, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file1 = tmpdir.mkdir('source1').join('catalog.yml')
    remote_catalog_file1.write(
        'all:\n  foovideos:\n    name: Videos from Foo')
    remote_catalog_file2 = tmpdir.mkdir('source2').join('catalog.yml')
    remote_catalog_file2.write(
        'all:\n  barbooks:\n    name: Books from Bar')

    expected = [
        {
            'id': 'foo', 'name': 'Content from Foo',
            'url': 'file://{}'.format(remote_catalog_file1.strpath),
            },
        {
            'id': 'bar', 'name': 'Content from Bar',
            'url': 'file://{}'.format(remote_catalog_file2.strpath),
            },
        ]

    for remote in expected:
        call_command(
            'catalog', 'remotes', 'add', remote['id'], remote['name'],
            remote['url'])

    call_command('catalog', 'remotes', 'list')

    out, err = capsys.readouterr()
    assert out.strip('\n').split('\n') == [
        "             [{0[id]}] {0[name]} : {0[url]}".format(r)
        for r in sorted(expected, key=itemgetter('id'))
        ]
    assert err.strip() == ''


def test_add_then_remove_then_list_remote(
        tmpdir, settings, capsys, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file = tmpdir.mkdir('source1').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    expected = {
        'id': 'foo', 'name': 'Content from Foo',
        'url': 'file://{}'.format(remote_catalog_file.strpath),
        }

    call_command(
        'catalog', 'remotes', 'add', expected['id'], expected['name'],
        expected['url'])
    call_command('catalog', 'remotes', 'remove', expected['id'])
    call_command('catalog', 'remotes', 'list')

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_update_cache_without_remote(tmpdir, settings, capsys):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    expected = {'installed': {}, 'available': {}}

    call_command('catalog', 'cache', 'update')
    assert tmpdir.join('catalog.yml').check(file=True)

    with tmpdir.join('catalog.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == expected

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_update_cache_with_remote(tmpdir, settings, capsys, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    remote = {
        'id': 'foo', 'name': 'Content from Foo',
        'url': 'file://{}'.format(remote_catalog_file.strpath),
        }

    call_command(
        'catalog', 'remotes', 'add', remote['id'], remote['name'],
        remote['url'])

    # Now let's say the remote published an update to their catalog
    remote_catalog_file = tmpdir.join('source', 'catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Great videos from Foo')

    call_command('catalog', 'cache', 'update')
    assert tmpdir.join('catalog.yml').check(file=True)

    expected = {'installed': {}, 'available': {
        'foovideos': {'name': 'Great videos from Foo'},
        }}

    with tmpdir.join('catalog.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == expected

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''


def test_clear_cache(tmpdir, settings, capsys, monkeypatch):
    settings.CATALOG_CACHE_BASE_DIR = tmpdir.strpath

    monkeypatch.setattr(
        'ideascube.serveradmin.catalog.urlretrieve', fake_urlretrieve)

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    remote = {
        'id': 'foo', 'name': 'Content from Foo',
        'url': 'file://{}'.format(remote_catalog_file.strpath),
        }
    expected = {'installed': {}, 'available': {}}

    call_command(
        'catalog', 'remotes', 'add', remote['id'], remote['name'],
        remote['url'])
    call_command('catalog', 'cache', 'update')

    call_command('catalog', 'cache', 'clear')
    assert tmpdir.join('catalog.yml').check(file=True)

    with tmpdir.join('catalog.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == expected

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == ''
