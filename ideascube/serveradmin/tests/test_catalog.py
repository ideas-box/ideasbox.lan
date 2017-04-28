import os
from hashlib import sha256
import zipfile

from py.path import local as Path
import pytest

from ideascube.mediacenter.models import Document


@pytest.fixture(
    params=[
        {
            'id': 'foo',
            'name': 'Content provided by Foo',
            'url': 'http://foo.fr/catalog.yml',
        },
        {
            'id': 'bibliothèque',
            'name': 'Le contenu de la bibliothèque',
            'url': 'http://foo.fr/catalog.yml',
        },
        {
            'name': 'Content provided by Foo',
            'url': 'http://foo.fr/catalog.yml',
        },
        {
            'id': 'foo',
            'url': 'http://foo.fr/catalog.yml',
        },
        {
            'id': 'foo',
            'name': 'Content provided by Foo',
        },
    ],
    ids=[
        'foo',
        'utf8',
        'missing-id',
        'missing-name',
        'missing-url',
    ])
def input_file(tmpdir, request):
    path = tmpdir.join('foo.yml')

    lines = []

    if 'id' in request.param:
        lines.append('id: {id}'.format(**request.param))

    if 'name' in request.param:
        lines.append('name: {name}'.format(**request.param))

    if 'url' in request.param:
        lines.append('url: "{url}"'.format(**request.param))

    path.write_text('\n'.join(lines), encoding='utf-8')

    return {'path': path.strpath, 'input': request.param}


@pytest.fixture
def zippedzim_path(testdatadir, tmpdir):
    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = tmpdir.mkdir('packages').join('wikipedia.tum-2015-08')
    zippedzim.copy(path)

    return path


@pytest.fixture
def staticsite_path(testdatadir, tmpdir):
    zipfile = testdatadir.join('catalog', 'w2eu-2016-02-26')
    path = tmpdir.mkdir('packages').join('w2eu-2016-02-26')
    zipfile.copy(path)
    return path


@pytest.fixture
def zippedmedia_path(testdatadir, tmpdir):
    zipfile = testdatadir.join('catalog', 'test-media.zip')
    path = tmpdir.mkdir('packages').join('test-media.zip')
    zipfile.copy(path)
    return path


@pytest.fixture
def install_dir(tmpdir):
    return tmpdir.mkdir('install')


def test_remote_from_file(input_file):
    from ideascube.serveradmin.catalog import InvalidFile, Remote

    path = input_file['path']
    expected_id = input_file['input'].get('id')
    expected_name = input_file['input'].get('name')
    expected_url = input_file['input'].get('url')

    if expected_id is None:
        with pytest.raises(InvalidFile) as exc:
            Remote.from_file(path)

        assert 'id' in exc.exconly()

    elif expected_name is None:
        with pytest.raises(InvalidFile) as exc:
            Remote.from_file(path)

        assert 'name' in exc.exconly()

    elif expected_url is None:
        with pytest.raises(InvalidFile) as exc:
            Remote.from_file(path)

        assert 'url' in exc.exconly()

    else:
        remote = Remote.from_file(path)
        assert remote.id == expected_id
        assert remote.name == expected_name
        assert remote.url == expected_url


def test_remote_to_file(tmpdir):
    from ideascube.serveradmin.catalog import Remote

    path = tmpdir.join('foo.yml')

    remote = Remote(
        'foo', 'Content provided by Foo', 'http://foo.fr/catalog.yml')
    remote.to_file(path.strpath)

    lines = path.readlines(cr=False)
    lines = filter(lambda x: len(x), lines)
    lines = sorted(lines)

    assert lines == [
        'id: foo', 'name: Content provided by Foo',
        'url: http://foo.fr/catalog.yml']


def test_remote_to_file_utf8(tmpdir):
    from ideascube.serveradmin.catalog import Remote

    path = tmpdir.join('foo.yml')

    remote = Remote(
        'bibliothèque', 'Le contenu de la bibliothèque',
        'http://foo.fr/catalog.yml')
    remote.to_file(path.strpath)

    lines = path.read_text('utf-8').split('\n')
    lines = filter(lambda x: len(x), lines)
    lines = sorted(lines)

    assert lines == [
        'id: "biblioth\\xE8que"', 'name: "Le contenu de la biblioth\\xE8que"',
        'url: http://foo.fr/catalog.yml']

    # Try loading it back
    remote = Remote.from_file(path.strpath)
    assert remote.id == 'bibliothèque'
    assert remote.name == 'Le contenu de la bibliothèque'


def test_package():
    from ideascube.serveradmin.catalog import Package

    p = Package('wikipedia.fr', {
        'name': 'Wikipédia en français', 'version': '2015-08'})
    assert p.id == 'wikipedia.fr'
    assert p.name == 'Wikipédia en français'
    assert p.version == '2015-08'

    with pytest.raises(AttributeError):
        print(p.no_such_attribute)

    with pytest.raises(NotImplementedError):
        p.install('some-path', 'some-other-path')

    with pytest.raises(NotImplementedError):
        p.remove('some-path')


def test_package_without_version():
    from ideascube.serveradmin.catalog import Package

    p = Package('wikipedia.fr', {'name': 'Wikipédia en français'})
    assert p.id == 'wikipedia.fr'
    assert p.name == 'Wikipédia en français'
    assert p.version == '0'


def test_package_equality():
    from ideascube.serveradmin.catalog import Package

    p1 = Package('wikipedia.fr', {
        'name': 'Wikipédia en français', 'version': '2015-08',
        'type': 'zippedzim'})
    p2 = Package('wikipedia.en', {
        'name': 'Wikipédia en français', 'version': '2015-08',
        'type': 'zippedzim'})
    assert p1 != p2

    p3 = Package('wikipedia.fr', {
        'name': 'Wikipédia en français', 'version': '2015-09',
        'type': 'zippedzim'})
    assert p1 != p3

    p4 = Package('wikipedia.fr', {
        'name': 'Wikipédia en français', 'type': 'zippedzim',
        'version': '2015-08'})
    assert p1 == p4


def test_filesize_should_render_int_size_as_human_friendly():
    from ideascube.serveradmin.catalog import Package

    p = Package('wikipedia.fr', {'name': 'Wikipédia', 'size': 287325597})
    assert p.filesize == '274.0 MB'


def test_filesize_should_render_str_size_as_is():
    from ideascube.serveradmin.catalog import Package

    p = Package('wikipedia.fr', {'name': 'Wikipédia', 'size': '1.7 GB'})
    assert p.filesize == '1.7 GB'


def test_package_registry():
    from ideascube.serveradmin.catalog import Package

    # Ensure the base type itself is not added to the registry
    assert Package not in Package.registered_types.values()

    # Register a new package type, make sure it gets added to the registry
    class RegisteredPackage(Package):
        typename = 'tests-only'

    assert Package.registered_types['tests-only'] == RegisteredPackage

    # Define a new package type without a typename attribute, make sure it
    # does **not** get added to the registry
    class NotRegisteredPackage(Package):
        pass

    assert NotRegisteredPackage not in Package.registered_types.values()


def test_install_zippedzim(zippedzim_path, install_dir):
    from ideascube.serveradmin.catalog import ZippedZim

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    p.install(zippedzim_path.strpath, install_dir.strpath)

    data = install_dir.join('data')
    assert data.check(dir=True)

    content = data.join('content')
    assert content.check(dir=True)
    assert content.join('{}.zim'.format(p.id)).check(file=True)

    lib = data.join('library')
    assert lib.check(dir=True)
    assert lib.join('{}.zim.xml'.format(p.id)).check(file=True)

    index = data.join('index')
    assert index.check(dir=True)
    assert index.join('{}.zim.idx'.format(p.id)).check(dir=True)


def test_install_invalid_zippedzim(tmpdir, testdatadir, install_dir):
    from ideascube.serveradmin.catalog import ZippedZim, InvalidFile

    src = testdatadir.join('backup', 'musasa-0.1.0-201501241620.tar')
    path = tmpdir.mkdir('packages').join('wikipedia.tum-2015-08')
    src.copy(path)

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})

    with pytest.raises(InvalidFile) as exc:
        p.install(path.strpath, install_dir.strpath)

    assert 'not a zip file' in exc.exconly()


def test_remove_zippedzim(zippedzim_path, install_dir):
    from ideascube.serveradmin.catalog import ZippedZim

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    p.install(zippedzim_path.strpath, install_dir.strpath)

    p.remove(install_dir.strpath)

    data = install_dir.join('data')
    assert data.check(dir=True)

    content = data.join('content')
    assert content.check(dir=True)
    assert content.join('{}.zim'.format(p.id)).check(exists=False)

    lib = data.join('library')
    assert lib.check(dir=True)
    assert lib.join('{}.zim.xml'.format(p.id)).check(exists=False)

    index = data.join('index')
    assert index.check(dir=True)
    assert index.join('{}.zim.idx'.format(p.id)).check(exists=False)


def test_install_staticsite(staticsite_path, install_dir):
    from ideascube.serveradmin.catalog import StaticSite

    p = StaticSite('w2eu', {
        'url': 'https://foo.fr/w2eu-2016-02-26.zim'})
    p.install(staticsite_path.strpath, install_dir.strpath)

    root = install_dir.join('w2eu')
    assert root.check(dir=True)

    index = root.join('index.html')
    with index.open() as f:
        assert 'static content' in f.read()


def test_remove_staticsite(staticsite_path, install_dir):
    from ideascube.serveradmin.catalog import StaticSite

    p = StaticSite('w2eu', {
        'url': 'https://foo.fr/w2eu-2016-02-26.zim'})
    p.install(staticsite_path.strpath, install_dir.strpath)

    p.remove(install_dir.strpath)

    root = install_dir.join('w2eu')
    assert root.check(exists=False)


@pytest.mark.usefixtures('db')
def test_install_zippedmedia(zippedmedia_path, install_dir):
    from ideascube.serveradmin.catalog import ZippedMedias

    p = ZippedMedias('test-media', {
        'url': 'https://foo.fr/test-media.zip'})
    p.install(zippedmedia_path.strpath, install_dir.strpath)

    root = install_dir.join('test-media')
    assert root.check(dir=True)

    manifest = root.join('manifest.yml')
    assert manifest.exists()


@pytest.mark.usefixtures('db')
def test_install_zippedmedia_missing_manifest(tmpdir,
                                              zippedmedia_path,
                                              install_dir):
    from ideascube.serveradmin.catalog import (InvalidPackageContent,
                                               ZippedMedias)

    bad_zippedmedia_dir = tmpdir.mkdir('source')
    bad_zippedmedia_path = bad_zippedmedia_dir.join('bad-test-media.zip')

    with zipfile.ZipFile(zippedmedia_path.strpath) as orig, \
            zipfile.ZipFile(bad_zippedmedia_path.strpath, mode='w') as bad:
        names = filter(lambda n: n != 'manifest.yml', orig.namelist())

        for name in names:
            if name == 'manifest.yml':
                continue

            orig.extract(name, bad_zippedmedia_dir.strpath)
            bad.write(bad_zippedmedia_dir.join(name).strpath, arcname=name)
            bad_zippedmedia_dir.join(name).remove()

    with pytest.raises(InvalidPackageContent):
        p = ZippedMedias('test-media', {
            'url': 'https://foo.fr/bad-test-media.zip'})
        p.install(bad_zippedmedia_path.strpath, install_dir.strpath)


@pytest.mark.usefixtures('db')
def test_remove_zippedmedia(zippedmedia_path, install_dir):
    from ideascube.serveradmin.catalog import ZippedMedias

    p = ZippedMedias('test-media', {
        'url': 'https://foo.fr/test-media.zip'})
    p.install(zippedmedia_path.strpath, install_dir.strpath)

    p.remove(install_dir.strpath)

    root = install_dir.join('w2eu')
    assert root.check(exists=False)


def test_handler(settings):
    from ideascube.serveradmin.catalog import Handler

    h = Handler()
    assert h._install_dir == settings.CATALOG_HANDLER_INSTALL_DIR


def test_kiwix_installs_zippedzim(settings, zippedzim_path):
    from ideascube.serveradmin.catalog import Kiwix, ZippedZim

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    h = Kiwix()
    h.install(p, zippedzim_path.strpath)

    install_root = Path(settings.CATALOG_KIWIX_INSTALL_DIR)

    data = install_root.join('data')
    assert data.check(dir=True)

    content = data.join('content')
    assert content.check(dir=True)
    assert content.join('{}.zim'.format(p.id)).check(file=True)

    lib = data.join('library')
    assert lib.check(dir=True)
    assert lib.join('{}.zim.xml'.format(p.id)).check(file=True)

    index = data.join('index')
    assert index.check(dir=True)
    assert index.join('{}.zim.idx'.format(p.id)).check(dir=True)


def test_kiwix_does_not_fail_if_files_already_exist(settings, zippedzim_path):
    from ideascube.serveradmin.catalog import Kiwix, ZippedZim

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    h = Kiwix()
    h.install(p, zippedzim_path.strpath)
    h.install(p, zippedzim_path.strpath)

    install_root = Path(settings.CATALOG_KIWIX_INSTALL_DIR)

    data = install_root.join('data')
    assert data.check(dir=True)


def test_kiwix_removes_zippedzim(settings, zippedzim_path):
    from ideascube.serveradmin.catalog import Kiwix, ZippedZim

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    h = Kiwix()
    h.install(p, zippedzim_path.strpath)

    h.remove(p)

    install_root = Path(settings.CATALOG_KIWIX_INSTALL_DIR)

    data = install_root.join('data')
    assert data.check(dir=True)

    content = data.join('content')
    assert content.check(dir=True)
    assert content.join('{}.zim'.format(p.id)).check(exists=False)

    lib = data.join('library')
    assert lib.check(dir=True)
    assert lib.join('{}.zim.xml'.format(p.id)).check(exists=False)

    index = data.join('index')
    assert index.check(dir=True)
    assert index.join('{}.zim.idx'.format(p.id)).check(exists=False)


@pytest.mark.usefixtures('db', 'systemuser')
def test_kiwix_commits_after_install(settings, zippedzim_path, mocker):
    from ideascube.serveradmin.catalog import Kiwix, ZippedZim

    manager = mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    h = Kiwix()
    h.install(p, zippedzim_path.strpath)
    h.commit()

    install_root = Path(settings.CATALOG_KIWIX_INSTALL_DIR)

    library = install_root.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata

    manager().get_service.assert_called_once_with('kiwix-server')
    manager().restart.call_count == 1


@pytest.mark.usefixtures('db', 'systemuser')
def test_kiwix_commits_after_remove(settings, zippedzim_path, mocker):
    from ideascube.serveradmin.catalog import Kiwix, ZippedZim
    from ideascube.serveradmin.systemd import NoSuchUnit

    manager = mocker.patch('ideascube.serveradmin.catalog.SystemManager')
    manager().get_service.side_effect = NoSuchUnit

    p = ZippedZim('wikipedia.tum', {
        'url': 'https://foo.fr/wikipedia_tum_all_nopic_2015-08.zim'})
    h = Kiwix()
    h.install(p, zippedzim_path.strpath)
    h.commit()

    assert manager().get_service.call_count == 1
    manager().restart.assert_not_called()

    h.remove(p)
    h.commit()

    install_root = Path(settings.CATALOG_KIWIX_INSTALL_DIR)

    library = install_root.join('library.xml')
    assert library.check(exists=True)
    assert library.read_text('utf-8') == (
        "<?xml version='1.0' encoding='utf-8'?>\n<library/>")

    assert manager().get_service.call_count == 2
    manager().restart.assert_not_called()


def test_nginx_installs_staticsite(settings, staticsite_path):
    from ideascube.serveradmin.catalog import Nginx, StaticSite

    p = StaticSite('w2eu', {})
    h = Nginx()
    h.install(p, staticsite_path.strpath)

    install_root = Path(settings.CATALOG_NGINX_INSTALL_DIR)

    root = install_root.join('w2eu')
    assert root.check(dir=True)

    index = root.join('index.html')
    with index.open() as f:
        assert 'static content' in f.read()


def test_nginx_removes_staticsite(settings, staticsite_path):
    from ideascube.serveradmin.catalog import Nginx, StaticSite

    p = StaticSite('w2eu', {})
    h = Nginx()
    h.install(p, staticsite_path.strpath)

    h.remove(p)

    install_root = Path(settings.CATALOG_NGINX_INSTALL_DIR)

    root = install_root.join('w2eu')
    assert root.check(exists=False)


@pytest.mark.usefixtures('db', 'systemuser')
def test_nginx_commits_after_install(settings, staticsite_path, mocker):
    from ideascube.serveradmin.catalog import Nginx, StaticSite

    manager = mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    p = StaticSite('w2eu', {})
    h = Nginx()
    h.install(p, staticsite_path.strpath)
    h.commit()

    manager().get_service.assert_called_once_with('nginx')
    manager().restart.call_count == 1


@pytest.mark.usefixtures('db', 'systemuser')
def test_nginx_commits_after_remove(settings, staticsite_path, mocker):
    from ideascube.serveradmin.catalog import Nginx, StaticSite
    from ideascube.serveradmin.systemd import NoSuchUnit

    manager = mocker.patch('ideascube.serveradmin.catalog.SystemManager')
    manager().get_service.side_effect = NoSuchUnit

    p = StaticSite('w2eu', {})
    h = Nginx()
    h.install(p, staticsite_path.strpath)
    h.commit()

    assert manager().get_service.call_count == 1
    manager().restart.assert_not_called()

    h.remove(p)
    h.commit()

    assert manager().get_service.call_count == 2
    manager().restart.assert_not_called()


@pytest.mark.usefixtures('db')
def test_mediacenter_installs_zippedmedia(settings, zippedmedia_path):
    from ideascube.serveradmin.catalog import MediaCenter, ZippedMedias

    assert Document.objects.count() == 0

    p = ZippedMedias('test-media', {
        'url': 'https://foo.fr/test-media.zip'})
    h = MediaCenter()
    h.install(p, zippedmedia_path.strpath)

    install_root = Path(settings.CATALOG_MEDIACENTER_INSTALL_DIR)

    root = install_root.join('test-media')
    assert root.check(dir=True)

    manifest = root.join('manifest.yml')
    assert manifest.exists()

    assert Document.objects.count() == 3
    video = Document.objects.get(title='my video')
    assert video.summary == 'my video summary'
    assert video.kind == Document.VIDEO
    assert Document.objects.search('summary').count() == 3

    documents_tag1 = Document.objects.search(tags=['tag1'])
    documents_tag1 = set(d.title for d in documents_tag1)
    assert documents_tag1 == set(['my video', 'my doc'])

    documents_tag2 = Document.objects.search(tags=['tag2'])
    documents_tag2 = set(d.title for d in documents_tag2)
    assert documents_tag2 == set(['my video', 'my image'])

    documents_tag3 = Document.objects.search(tags=['tag3'])
    documents_tag3 = set(d.title for d in documents_tag3)
    assert documents_tag3 == set(['my video'])

    documents_tag4 = Document.objects.search(tags=['tag4'])
    documents_tag4 = set(d.title for d in documents_tag4)
    assert documents_tag4 == set(['my doc'])

    packaged_documents = Document.objects.filter(package_id='test-media')
    assert packaged_documents.count() == 3

    # Be sure that referenced documents are the ones installed by the package
    # and are not copied somewhere by the django media system.
    for document in packaged_documents:
        path = os.path.realpath(document.original.path)
        dirname = os.path.dirname(path)
        assert dirname.startswith(install_root.join('test-media').strpath)


@pytest.mark.usefixtures('db')
def test_mediacenter_removes_zippedmedia(tmpdir, settings, zippedmedia_path):
    from ideascube.serveradmin.catalog import MediaCenter, ZippedMedias

    p = ZippedMedias('test-media', {
        'url': 'https://foo.fr/test-media.zip'})
    h = MediaCenter()
    h.install(p, zippedmedia_path.strpath)

    assert Document.objects.count() == 3

    h.remove(p)

    assert Document.objects.count() == 0

    install_root = Path(settings.CATALOG_MEDIACENTER_INSTALL_DIR)

    root = install_root.join('test-media')
    assert root.check(exists=False)


def test_catalog_no_remote(settings):
    from ideascube.serveradmin.catalog import Catalog

    c = Catalog()
    assert c.list_remotes() == []

    remotes_dir = Path(settings.CATALOG_STORAGE_ROOT).join('remotes')

    assert remotes_dir.check(dir=True)
    assert remotes_dir.listdir() == []


def test_catalog_existing_remote(settings):
    from ideascube.serveradmin.catalog import Catalog

    params = {
        'id': 'foo', 'name': 'Content provided by Foo',
        'url': 'http://foo.fr/catalog.yml'}

    remotes_dir = Path(settings.CATALOG_STORAGE_ROOT).mkdir('remotes')
    remotes_dir.join('foo.yml').write(
        'id: {id}\nname: {name}\nurl: {url}'.format(**params))

    c = Catalog()
    remotes = c.list_remotes()
    assert len(remotes) == 1

    remote = remotes[0]
    assert remote.id == params['id']
    assert remote.name == params['name']
    assert remote.url == params['url']


def test_catalog_add_remotes():
    from ideascube.serveradmin.catalog import Catalog, ExistingRemoteError

    c = Catalog()
    c.add_remote('foo', 'Content provided by Foo', 'http://foo.fr/catalog.yml')
    remotes = c.list_remotes()
    assert len(remotes) == 1

    remote = remotes[0]
    assert remote.id == 'foo'
    assert remote.name == 'Content provided by Foo'
    assert remote.url == 'http://foo.fr/catalog.yml'

    c.add_remote('bar', 'Content provided by Bar', 'http://bar.fr/catalog.yml')
    remotes = c.list_remotes()
    assert len(remotes) == 2

    remote = remotes[0]
    assert remote.id == 'bar'
    assert remote.name == 'Content provided by Bar'
    assert remote.url == 'http://bar.fr/catalog.yml'

    remote = remotes[1]
    assert remote.id == 'foo'
    assert remote.name == 'Content provided by Foo'
    assert remote.url == 'http://foo.fr/catalog.yml'

    with pytest.raises(ExistingRemoteError) as exc:
        c.add_remote('foo', 'Content by Foo', 'http://foo.fr/catalog.yml')

    assert 'foo' in exc.exconly()


def test_catalog_remove_remote(settings):
    from ideascube.serveradmin.catalog import Catalog

    params = {
        'id': 'foo', 'name': 'Content provided by Foo',
        'url': 'http://foo.fr/catalog.yml'}

    remotes_dir = Path(settings.CATALOG_STORAGE_ROOT).mkdir('remotes')
    remotes_dir.join('foo.yml').write(
        'id: {id}\nname: {name}\nurl: {url}'.format(**params))

    c = Catalog()
    c.remove_remote(params['id'])
    remotes = c.list_remotes()
    assert len(remotes) == 0

    with pytest.raises(ValueError) as exc:
        c.remove_remote(params['id'])

    assert params['id'] in exc.exconly()


def test_catalog_update_cache(tmpdir, monkeypatch):
    from ideascube.serveradmin.catalog import Catalog

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    c = Catalog()
    assert c._available == {}
    assert c._installed == {}

    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    assert c._available == {'foovideos': {'name': 'Videos from Foo'}}
    assert c._installed == {}

    c = Catalog()
    assert c._available == {'foovideos': {'name': 'Videos from Foo'}}
    assert c._installed == {}


def test_catalog_update_cache_no_fail_if_remote_unavailable(mocker):
    from ideascube.serveradmin.catalog import Catalog
    from requests import ConnectionError

    mocker.patch('ideascube.serveradmin.catalog.urlretrieve',
                 side_effect=ConnectionError)

    c = Catalog()
    assert c._available == {}
    assert c._installed == {}

    c.add_remote(
        'foo', 'Content from Foo', 'http://example.com/not_existing')
    c.update_cache()
    assert c._available == {}
    assert c._installed == {}


def test_catalog_update_cache_updates_installed_metadata(tmpdir, monkeypatch):
    from ideascube.serveradmin.catalog import Catalog

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n'
        '  foovideos:\n'
        '    name: Videos from Foo\n'
        '    sha256sum: abcdef\n'
        '    type: zipped-zim\n'
        '    version: 1.0.0\n'
    )

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    assert c._available == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}
    assert c._installed == {}

    # Let's pretend we've installed stuff here
    c._installed_value = c._available.copy()
    c._persist_catalog()
    assert c._available == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}
    assert c._installed == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}

    # And now let's say that someone modified the remote metadata, for example
    # to fix an undescriptive name
    remote_catalog_file.write(
        'all:\n'
        '  foovideos:\n'
        '    name: Awesome videos from Foo\n'
        '    sha256sum: abcdef\n'
        '    type: zipped-zim\n'
        '    version: 1.0.0\n'
    )

    c.update_cache()
    assert c._available == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Awesome videos from Foo'}}
    assert c._installed == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Awesome videos from Foo'}}


def test_catalog_update_cache_does_not_update_installed_metadata(tmpdir, monkeypatch):
    from ideascube.serveradmin.catalog import Catalog

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n'
        '  foovideos:\n'
        '    name: Videos from Foo\n'
        '    sha256sum: abcdef\n'
        '    type: zipped-zim\n'
        '    version: 1.0.0\n'
    )

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    assert c._available == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}
    assert c._installed == {}

    # Let's pretend we've installed stuff here
    c._installed_value = c._available.copy()
    c._persist_catalog()
    assert c._available == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}
    assert c._installed == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}

    # And now let's say that someone modified the remote metadata, for example
    # to fix an undescriptive name... while also publishing an update
    remote_catalog_file.write(
        'all:\n'
        '  foovideos:\n'
        '    name: Awesome videos from Foo\n'
        '    sha256sum: abcdef\n'
        '    type: zipped-zim\n'
        '    version: 2.0.0\n'
    )

    c.update_cache()
    assert c._available == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '2.0.0',
        'name': 'Awesome videos from Foo'}}
    assert c._installed == {'foovideos': {
        'sha256sum': 'abcdef', 'type': 'zipped-zim', 'version': '1.0.0',
        'name': 'Videos from Foo'}}


def test_catalog_clear_cache(tmpdir, monkeypatch):
    from ideascube.serveradmin.catalog import Catalog

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    remote_catalog_file.write(
        'all:\n  foovideos:\n    name: Videos from Foo')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    assert c._available == {}
    assert c._installed == {}

    c.update_cache()
    assert c._available == {'foovideos': {'name': 'Videos from Foo'}}
    assert c._installed == {}

    c.clear_cache()
    assert c._available == {}
    assert c._installed == {}


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package_glob(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.*'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package_twice(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    # Once to download the remote catalog.yml, once to download the package

    c.install_packages(['wikipedia.tum'])


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_does_not_stop_on_failure(tmpdir, settings,
                                                  testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zip')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')
        f.write('  wikipedia.fr:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    def fake_install(package, download_path):
        if package.id == 'wikipedia.tum':
            raise OSError

    spy_install = mocker.patch(
        'ideascube.serveradmin.catalog.Kiwix.install',
        side_effect=fake_install)

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum', 'wikipedia.fr'])

    assert spy_install.call_count == 2
    assert 'wikipedia.tum' not in c._installed
    assert 'wikipedia.fr' in c._installed


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package_already_downloaded(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    cachedir = Path(settings.CATALOG_CACHE_ROOT)
    packagesdir = cachedir.mkdir('packages')
    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(packagesdir.join('wikipedia.tum-2015-08'))

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package_already_in_additional_cache(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')
    additionaldir = tmpdir.mkdir('this-could-be-a-usb-stick')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(additionaldir.join('wikipedia.tum-2015-08'))

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.add_package_cache(additionaldir.strpath)
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package_partially_downloaded(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    cachedir = Path(settings.CATALOG_CACHE_ROOT)
    packagesdir = cachedir.mkdir('packages')
    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    # Partially download the package
    packagesdir.join('wikipedia.tum-2015-08').write_binary(
        zippedzim.read_binary()[:100])

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_install_package_partially_downloaded_but_corrupted(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    cachedir = Path(settings.CATALOG_CACHE_ROOT)
    packagesdir = cachedir.mkdir('packages')
    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    # Partially download the package
    packagesdir.join('wikipedia.tum-2015-08').write_binary(
        b'corrupt download')

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata


def test_catalog_install_package_does_not_exist(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog, NoSuchPackage

    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()

    with pytest.raises(NoSuchPackage):
        c.install_packages(['nosuchpackage'])


def test_catalog_install_package_with_missing_type(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog, InvalidPackageMetadata

    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()

    with pytest.raises(InvalidPackageMetadata):
        c.install_packages(['wikipedia.tum'])


def test_catalog_install_package_with_unknown_type(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog, InvalidPackageType

    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: something-not-supported\n')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()

    with pytest.raises(InvalidPackageType):
        c.install_packages(['wikipedia.tum'])


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_reinstall_package(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    zim = installdir.join('data', 'content', 'wikipedia.tum.zim')
    assert zim.check(file=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata

    # Now let's pretend a hacker modified the file
    good_hash = sha256(zim.read_binary())
    zim.write_text('你好嗎？', encoding='utf-8')

    # And now, reinstall
    c.reinstall_packages(['wikipedia.tum'])

    assert sha256(zim.read_binary()).hexdigest() == good_hash.hexdigest()
    assert zim.read_binary() != '你好嗎？'.encode('utf-8')


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_remove_package(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])
    c.remove_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)
    assert library.read_text('utf-8') == (
        "<?xml version='1.0' encoding='utf-8'?>\n<library/>")


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_remove_package_glob(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])
    c.remove_packages(['wikipedia.*'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)
    assert library.read_text('utf-8') == (
        "<?xml version='1.0' encoding='utf-8'?>\n<library/>")


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_update_package(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata
        assert 'date="2015-08-10"' in libdata

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-09')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-09.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-09\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: f8794e3c8676258b0b594ad6e464177dda8d66dbcbb04b301'
            'd78fd4c9cf2c3dd\n')
        f.write('    type: zipped-zim\n')

    c.update_cache()
    c.upgrade_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata
        assert 'date="2015-09-10"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_update_package_glob(tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata
        assert 'date="2015-08-10"' in libdata

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-09')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-09.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-09\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: f8794e3c8676258b0b594ad6e464177dda8d66dbcbb04b301'
            'd78fd4c9cf2c3dd\n')
        f.write('    type: zipped-zim\n')

    c.update_cache()
    c.upgrade_packages(['wikipedia.*'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    with library.open(mode='r') as f:
        libdata = f.read()

        assert 'path="data/content/wikipedia.tum.zim"' in libdata
        assert 'indexPath="data/index/wikipedia.tum.zim.idx"' in libdata
        assert 'date="2015-09-10"' in libdata


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_update_package_already_latest(
        tmpdir, settings, testdatadir, mocker, capsys):
    from ideascube.serveradmin.catalog import Catalog

    installdir = Path(settings.CATALOG_KIWIX_INSTALL_DIR)
    sourcedir = tmpdir.mkdir('source')

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = sourcedir.join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = sourcedir.join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    library = installdir.join('library.xml')
    assert library.check(exists=True)

    old_mtime = library.mtime()

    # Drop what was logged so far
    capsys.readouterr()

    c.upgrade_packages(['wikipedia.tum'])

    assert library.mtime() == old_mtime

    out, err = capsys.readouterr()
    assert out.strip() == ''
    assert err.strip() == 'wikipedia.tum has no update available'


def test_catalog_list_available_packages(tmpdir, monkeypatch):
    from ideascube.serveradmin.catalog import Catalog, ZippedZim

    remote_catalog_file = tmpdir.mkdir('source').join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  foovideos:\n')
        f.write('    name: Videos from Foo\n')
        f.write('    type: zipped-zim\n')
        f.write('    version: 1.0.0\n')
        f.write('    size: 1GB\n')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()

    pkgs = c.list_available(['nosuchpackage'])
    assert len(pkgs) == 0

    pkgs = c.list_available(['foovideos'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'foovideos'
    assert pkg.name == 'Videos from Foo'
    assert pkg.version == '1.0.0'
    assert pkg.size == '1GB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_available(['foo*'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'foovideos'
    assert pkg.name == 'Videos from Foo'
    assert pkg.version == '1.0.0'
    assert pkg.size == '1GB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_available(['*videos'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'foovideos'
    assert pkg.name == 'Videos from Foo'
    assert pkg.version == '1.0.0'
    assert pkg.size == '1GB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_available(['*'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'foovideos'
    assert pkg.name == 'Videos from Foo'
    assert pkg.version == '1.0.0'
    assert pkg.size == '1GB'
    assert isinstance(pkg, ZippedZim)


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_list_installed_packages(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog, ZippedZim

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = tmpdir.mkdir('source').join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = tmpdir.join('source').join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])

    pkgs = c.list_installed(['nosuchpackage'])
    assert len(pkgs) == 0

    pkgs = c.list_installed(['wikipedia.tum'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-08'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_installed(['wikipedia.*'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-08'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_installed(['*.tum'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-08'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_installed(['*'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-08'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_list_upgradable_packages(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog, ZippedZim

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = tmpdir.mkdir('source').join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = tmpdir.join('source').join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()
    c.install_packages(['wikipedia.tum'])
    assert c.list_upgradable(['*']) == []

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-09')
    path = tmpdir.join('source').join('wikipedia_tum_all_nopic_2015-09.zim')
    zippedzim.copy(path)

    remote_catalog_file = tmpdir.join('source').join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-09\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')

    c.update_cache()
    pkgs = c.list_upgradable(['nosuchpackage'])
    assert len(pkgs) == 0

    pkgs = c.list_upgradable(['wikipedia.tum'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-09'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_upgradable(['wikipedia.*'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-09'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_upgradable(['*.tum'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-09'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)

    pkgs = c.list_upgradable(['*'])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.id == 'wikipedia.tum'
    assert pkg.version == '2015-09'
    assert pkg.size == '200KB'
    assert isinstance(pkg, ZippedZim)


@pytest.mark.usefixtures('db', 'systemuser')
def test_catalog_list_nothandled_packages(
        tmpdir, settings, testdatadir, mocker):
    from ideascube.serveradmin.catalog import Catalog

    zippedzim = testdatadir.join('catalog', 'wikipedia.tum-2015-08')
    path = tmpdir.mkdir('source').join('wikipedia_tum_all_nopic_2015-08.zim')
    zippedzim.copy(path)

    remote_catalog_file = tmpdir.join('source').join('catalog.yml')
    with remote_catalog_file.open(mode='w') as f:
        f.write('all:\n')
        f.write('  wikipedia.tum:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 200KB\n')
        f.write('    url: file://{}\n'.format(path))
        f.write(
            '    sha256sum: 335d00b53350c63df45486c5433205f068ad90e33c208064b'
            '212c29a30109c54\n')
        f.write('    type: zipped-zim\n')
        f.write('  nothandled:\n')
        f.write('    version: 2015-08\n')
        f.write('    size: 0KB\n')
        f.write('    url: file://fackurl\n')
        f.write('    sha256sum: 0\n')
        f.write('    type: NOTHANDLED\n')

    mocker.patch('ideascube.serveradmin.catalog.SystemManager')

    c = Catalog()
    c.add_remote(
        'foo', 'Content from Foo',
        'file://{}'.format(remote_catalog_file.strpath))
    c.update_cache()

    pkgs = c.list_available(['*'])
    assert len(pkgs) == 1
    pkgs = c.list_nothandled(['*'])
    assert len(pkgs) == 1
    pkgs = c.list_installed(['*'])
    assert len(pkgs) == 0

    c.install_packages(['wikipedia.tum'])

    pkgs = c.list_available(['*'])
    assert len(pkgs) == 1
    pkgs = c.list_nothandled(['*'])
    assert len(pkgs) == 1
    pkgs = c.list_installed(['*'])
    assert len(pkgs) == 1


def test_catalog_doesn_t_try_to_read_file_at_instanciation(settings, mocker):
    from ideascube.serveradmin.catalog import Catalog
    from unittest.mock import mock_open
    m = mock_open()
    mocker.patch('builtins.open', m)

    c = Catalog()
    assert not m.called

    c._available
    assert m.called


def test_catalog_update_displayed_package(systemuser):
    from ideascube.configuration import get_config, set_config
    from ideascube.serveradmin.catalog import Catalog
    set_config('home-page', 'displayed-package-ids',
               ['id1', 'id2', 'id3'], systemuser)

    Catalog._update_displayed_packages_on_home(to_remove_ids=['id1', 'id4'])
    assert get_config('home-page', 'displayed-package-ids') == ['id2', 'id3']

    Catalog._update_displayed_packages_on_home(to_add_ids=['id2', 'id4', 'id4'])
    assert get_config('home-page', 'displayed-package-ids') \
        == ['id2', 'id3', 'id4']

    Catalog._update_displayed_packages_on_home(to_remove_ids=['id2', 'id4'],
                                               to_add_ids=['id1', 'id4'])
    assert get_config('home-page', 'displayed-package-ids') \
        == ['id3', 'id1', 'id4']
