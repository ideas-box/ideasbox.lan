from io import BytesIO
import os
import shutil
import tarfile

import pytest
from webtest.forms import Checkbox, Upload

from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile

from ..backup import Backup
from ideascube.configuration import get_config, set_config
from .test_backup import BACKUPS_ROOT, DATA_ROOT
from . import (
    FakeBus, FakePopen, FailingPopen, NMActiveConnection, NMConnection,
    NMDevice)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("page", [
    ("settings"),
    ("languages"),
    ("services"),
    ("power"),
    ("backup"),
    ("battery"),
    ("wifi"),
    ("wifi_history"),
])
def test_anonymous_user_should_not_access_server(app, page):
    response = app.get(reverse("server:" + page), status=302)
    assert "login" in response["Location"]


@pytest.mark.parametrize("page", [
    ("settings"),
    ("languages"),
    ("services"),
    ("power"),
    ("backup"),
    ("battery"),
    ("wifi"),
    ("wifi_history"),
])
def test_normals_user_should_not_access_server(loggedapp, page):
    response = loggedapp.get(reverse("server:" + page), status=302)
    assert "login" in response["Location"]


def test_staff_can_change_server_name(staffapp):
    res = staffapp.get(reverse('server:settings'), status=200)
    form = res.forms['server_name']
    assert form['server_name'].value == 'Ideas Cube'

    form['server_name'] = 'Test Name'
    res = form.submit()
    form = res.forms['server_name']
    assert form['server_name'].value == 'Test Name'


def test_staff_app_cannot_set_empty_server_name(staffapp):
    res = staffapp.get(reverse('server:settings'), status=200)
    form = res.forms['server_name']
    assert form['server_name'].value == 'Ideas Cube'

    form['server_name'] = ''
    res = form.submit()
    form = res.forms['server_name']
    assert form['server_name'].value == 'Ideas Cube'
    assert 'Server name cannot be empty' in res.unicode_body


def test_staff_is_presented_with_default_server_name(staffapp, settings):
    res = staffapp.get(reverse('server:settings'), status=200)
    form = res.forms['server_name']
    assert form['server_name'].value == 'Ideas Cube'


def test_staff_lists_services(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    settings.SERVICES = [
        {'name': 'foobar'}, {'name': 'nginx'},
        {'name': 'NetworkManager.service'}]

    res = staffapp.get(reverse("server:services"), status=200)
    body = res.unicode_body

    assert body.count('<li class="service">') == 3


def test_staff_lists_uninstalled_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    settings.SERVICES = [{'name': 'foobar'}]

    res = staffapp.get(reverse("server:services"), status=200)
    body = res.unicode_body

    assert body.count('<li class="service">') == 1
    assert '<h3>foobar <span>not running</span></h3>' in body
    assert '<div class="error">Not installed</div>' in body
    assert '<input type="submit" name="start" value="Start">' not in body
    assert '<input type="submit" name="restart" value="Restart">' not in body
    assert '<input type="submit" name="stop" value="Stop">' not in body


def test_staff_lists_inactive_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    settings.SERVICES = [{'name': 'nginx'}]

    res = staffapp.get(reverse("server:services"), status=200)
    body = res.unicode_body

    assert body.count('<li class="service">') == 1
    assert '<h3>nginx <span>not running</span></h3>' in body
    assert '<div class="error">Not installed</div>' not in body
    assert '<input type="submit" name="start" value="Start">' in body
    assert '<input type="submit" name="restart" value="Restart">' not in body
    assert '<input type="submit" name="stop" value="Stop">' not in body


def test_staff_lists_active_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    settings.SERVICES = [{'name': 'NetworkManager'}]

    res = staffapp.get(reverse("server:services"), status=200)
    body = res.unicode_body

    assert body.count('<li class="service">') == 1
    assert '<h3>NetworkManager <span>running</span></h3>' in body
    assert '<div class="error">Not installed</div>' not in body
    assert '<input type="submit" name="start" value="Start">' not in body
    assert '<input type="submit" name="restart" value="Restart">' in body
    assert '<input type="submit" name="stop" value="Stop">' in body


def test_staff_activates_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.Popen',
        side_effect=FakePopen)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.PIPE', side_effect=BytesIO)

    settings.SERVICES = [{'name': 'nginx'}]

    res = staffapp.get(reverse("server:services"), status=200)
    form = res.forms['service-nginx']
    res = form.submit('start')
    assert (
        '<ul class="messages"><li class="error">Could not enable '
        'nginx.service: Oh Noes!</li></ul>') not in res.unicode_body


def test_staff_fails_to_activate_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.Popen',
        side_effect=FailingPopen)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.PIPE', side_effect=BytesIO)

    settings.SERVICES = [{'name': 'nginx'}]

    res = staffapp.get(reverse("server:services"), status=200)
    form = res.forms['service-nginx']
    res = form.submit('start')
    assert (
        '<ul class="messages"><li class="error">Could not enable '
        'nginx.service: Oh Noes!</li></ul>') in res.unicode_body


def test_staff_deactivates_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.Popen',
        side_effect=FakePopen)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.PIPE', side_effect=BytesIO)

    settings.SERVICES = [{'name': 'NetworkManager'}]

    res = staffapp.get(reverse("server:services"), status=200)
    form = res.forms['service-NetworkManager']
    res = form.submit('stop')
    assert (
        '<ul class="messages"><li class="error">Could not disable '
        'NetworkManager.service: Oh Noes!</li></ul>') not in res.unicode_body


def test_staff_fails_to_deactivate_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.Popen',
        side_effect=FailingPopen)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.PIPE', side_effect=BytesIO)

    settings.SERVICES = [{'name': 'NetworkManager'}]

    res = staffapp.get(reverse("server:services"), status=200)
    form = res.forms['service-NetworkManager']
    res = form.submit('stop')
    assert (
        '<ul class="messages"><li class="error">Could not disable '
        'NetworkManager.service: Oh Noes!</li></ul>') in res.unicode_body


def test_staff_restarts_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.Popen',
        side_effect=FakePopen)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.PIPE', side_effect=BytesIO)

    settings.SERVICES = [{'name': 'NetworkManager'}]

    res = staffapp.get(reverse("server:services"), status=200)
    form = res.forms['service-NetworkManager']
    res = form.submit('restart')
    assert (
        '<ul class="messages"><li class="error">Could not restart '
        'NetworkManager.service: Oh Noes!</li></ul>') not in res.unicode_body


def test_staff_fails_to_restart_service(mocker, staffapp, settings):
    mocker.patch(
        'ideascube.serveradmin.systemd.dbus.SystemBus', side_effect=FakeBus)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.Popen',
        side_effect=FailingPopen)
    mocker.patch(
        'ideascube.serveradmin.systemd.subprocess.PIPE', side_effect=BytesIO)

    settings.SERVICES = [{'name': 'NetworkManager'}]

    res = staffapp.get(reverse("server:services"), status=200)
    form = res.forms['service-NetworkManager']
    res = form.submit('restart')
    assert (
        '<ul class="messages"><li class="error">Could not restart '
        'NetworkManager.service: Oh Noes!</li></ul>') in res.unicode_body


def test_staff_user_should_access_power_admin(staffapp):
    assert staffapp.get(reverse("server:power"), status=200)


def test_staff_user_should_access_backup_admin(staffapp):
    assert staffapp.get(reverse("server:backup"), status=200)


def test_backup_should_list_available_backups(staffapp, backup):
    form = staffapp.get(reverse('server:backup')).forms['backup']
    radio_options = form.get('backup').options
    assert len(radio_options) == 4
    assert radio_options[2][0] == backup.name


def test_backup_button_should_save_a_new_backup(staffapp, monkeypatch,
                                                settings):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.FORMAT', 'gztar')
    if os.path.exists(BACKUPS_ROOT):
        shutil.rmtree(BACKUPS_ROOT)
    filename = 'edoardo-0.0.0-201501231405.tar.gz'
    filepath = os.path.join(BACKUPS_ROOT, filename)
    try:
        # Make sure it doesn't exist before running backup.
        os.remove(filepath)
    except OSError:
        pass
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    monkeypatch.setattr('ideascube.serveradmin.backup.make_name',
                        lambda f: filename)
    proof_file = os.path.join(settings.BACKUPED_ROOT, 'backup.me')
    open(proof_file, mode='w')
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form.submit('do_create')
    assert os.path.exists(filepath)
    assert tarfile.is_tarfile(filepath)
    archive = tarfile.open(filepath)
    assert './backup.me' in archive.getnames()
    os.remove(filepath)
    os.remove(proof_file)


def test_restore_button_should_restore(staffapp, monkeypatch, settings,
                                       backup):
    assert len(os.listdir(DATA_ROOT)) == 4  # One by format.
    dbpath = os.path.join(settings.BACKUPED_ROOT, 'default.sqlite')
    assert not os.path.exists(dbpath)
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['backup'] = backup.name
    form.submit('do_restore')
    assert len(os.listdir(DATA_ROOT)) == 4
    assert os.path.exists(dbpath)
    os.remove(dbpath)


def test_download_button_should_download_tar_file(staffapp, backup, tmpdir):
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['backup'] = backup.name
    resp = form.submit('do_download')
    assert backup.name in resp['Content-Disposition']
    archive_name = os.path.join(str(tmpdir), 'backup.tar')
    with open(archive_name, mode="wb") as f:
        f.write(resp.content)
    assert tarfile.is_tarfile(archive_name)


def test_delete_button_should_remove_file(staffapp, backup):
    assert len(os.listdir(DATA_ROOT)) == 4
    with open(backup.path, mode='rb') as f:
        other = Backup.load(ContentFile(f.read(),
                            name='kavumu-0.1.0-201401241620.tar.gz'))
    assert len(os.listdir(DATA_ROOT)) == 5
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['backup'] = other.name
    form.submit('do_delete')
    assert len(os.listdir(DATA_ROOT)) == 4


def test_upload_button_create_new_backup_with_uploaded_file(staffapp,
                                                            monkeypatch):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    if os.path.exists(BACKUPS_ROOT):
        shutil.rmtree(BACKUPS_ROOT)
    backup_name = 'musasa-0.1.0-201501241620.tar.gz'
    backup_path = os.path.join(BACKUPS_ROOT, backup_name)
    assert not os.path.exists(backup_path)
    with open(os.path.join(DATA_ROOT, backup_name), mode='rb') as f:
        form = staffapp.get(reverse('server:backup')).forms['backup']
        form['upload'] = Upload(backup_name, f.read())
        form.submit('do_upload')
        assert os.path.exists(backup_path)
        os.remove(backup_path)


def test_upload_button_do_not_create_backup_with_non_tar_file(staffapp,
                                                              monkeypatch):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    backup_name = 'musasa-0.1.0-201501241620.tar'
    backup_path = os.path.join(BACKUPS_ROOT, backup_name)
    assert not os.path.exists(backup_path)
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['upload'] = Upload(backup_name, b'xxx')
    resp = form.submit('do_upload')
    assert resp.status_code == 200
    assert not os.path.exists(backup_path)


def test_upload_button_do_not_create_backup_with_bad_file_name(staffapp,
                                                               monkeypatch):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    backup_name = 'musasa-0.1.0-201501241620.tar'
    backup_path = os.path.join(BACKUPS_ROOT, backup_name)
    assert not os.path.exists(backup_path)
    with open(os.path.join(DATA_ROOT, backup_name), mode='rb') as f:
        form = staffapp.get(reverse('server:backup')).forms['backup']
        form['upload'] = Upload('badname.tar', f.read())
        resp = form.submit('do_upload')
        assert resp.status_code == 200
        assert not os.path.exists(backup_path)


def test_staff_user_should_access_battery_management(monkeypatch, staffapp):
    monkeypatch.setattr("subprocess.Popen", FakePopen)
    assert staffapp.get(reverse("server:battery"), status=200)


def test_staff_accesses_wifi_without_wireless(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = False

    res = staffapp.get(reverse("server:wifi"), status=200)
    assert 'Wi-Fi hardware is disabled' in res.unicode_body
    assert 'No Wi-Fi available' in res.unicode_body


def test_staff_lists_wifi_networks(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: []

    res = staffapp.get(reverse("server:wifi"), status=200)
    assert 'Wi-Fi hardware is disabled' not in res.unicode_body
    assert 'Wi-Fi is disabled' not in res.unicode_body
    assert 'No Wi-Fi available' not in res.unicode_body
    assert 'my home network' in res.unicode_body
    assert 'random open network' in res.unicode_body


def test_staff_connects_to_known_open_network(mocker, staffapp):
    def activate_connection(connection, device, path):
        NM.ActiveConnections.append(
            NMActiveConnection(ssid=connection.ssid))

    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.ActivateConnection.side_effect = activate_connection
    NM.ActiveConnections = []
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(True, ssid='random open network'),
        ]

    res = staffapp.get(reverse(
        "server:wifi", kwargs={'ssid': 'random open network'}), status=200)
    assert 'No Wi-Fi available' not in res.unicode_body
    assert "Connected to random open network" in res.unicode_body


def test_staff_connects_to_new_open_network(mocker, staffapp):
    def add_connection(settings):
        ssid = settings['802-11-wireless']['ssid']
        connection = NMConnection(True, ssid=ssid)

        NMSettings.ListConnections.side_effect = lambda: [connection]
        NM.ActiveConnections.append(NMActiveConnection(ssid=connection.ssid))

        return connection

    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.ActiveConnections = []
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.AddConnection.side_effect = add_connection
    NMSettings.ListConnections.side_effect = lambda: []

    res = staffapp.get(reverse(
        "server:wifi", kwargs={'ssid': 'random open network'}), status=200)
    assert 'No Wi-Fi available' not in res.unicode_body
    assert "Connected to random open network" in res.unicode_body
    assert NMSettings.AddConnection.call_count == 1


def test_staff_connects_to_known_wpa_network(mocker, staffapp):
    def activate_connection(connection, device, path):
        NM.ActiveConnections.append(
            NMActiveConnection(ssid=connection.ssid))

    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.ActivateConnection.side_effect = activate_connection
    NM.ActiveConnections = []
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(True, ssid='my home network'),
        ]

    res = staffapp.get(reverse(
        "server:wifi", kwargs={'ssid': 'my home network'}), status=200)
    assert 'No Wi-Fi available' not in res.unicode_body
    assert "Connected to my home network" in res.unicode_body


def test_staff_connects_to_new_wpa_network(mocker, staffapp):
    def add_connection(settings):
        ssid = settings['802-11-wireless']['ssid']
        connection = NMConnection(True, ssid=ssid)

        NMSettings.ListConnections.side_effect = lambda: [connection]
        NM.ActiveConnections.append(NMActiveConnection(ssid=connection.ssid))

        return connection

    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.ActiveConnections = []
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.AddConnection.side_effect = add_connection
    NMSettings.ListConnections.side_effect = lambda: []

    res = staffapp.post(reverse(
        "server:wifi", kwargs={'ssid': 'my home network'}),
        params={'csrfmiddlewaretoken': staffapp.cookies['csrftoken']},
        status=200)
    assert 'A key is required to connect to this network' in res.unicode_body
    assert NMSettings.AddConnection.call_count == 0

    res = staffapp.post(reverse(
        "server:wifi", kwargs={'ssid': 'my home network'}),
        params={
            'wifi_key': 'some wifi key',
            'csrfmiddlewaretoken': staffapp.cookies['csrftoken'],
            },
        status=200)
    assert "Connected to my home network" in res.unicode_body
    assert NMSettings.AddConnection.call_count == 1


def test_staff_connects_to_non_existing_network(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.ActiveConnections = []
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(True, ssid='my home network'),
        ]

    res = staffapp.get(reverse(
        "server:wifi", kwargs={'ssid': 'no such network'}), status=200)
    assert 'No Wi-Fi available' not in res.unicode_body
    assert "No such network: no such network" in res.unicode_body


def test_staff_accesses_wifi_history_without_wireless(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = False

    res = staffapp.get(reverse("server:wifi_history"), status=200)
    print(res.unicode_body)
    assert 'Wi-Fi hardware is disabled' in res.unicode_body
    assert 'No known Wi-Fi networks' in res.unicode_body


def test_staff_accesses_wifi_history(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(True, ssid='random open network', is_secure=False),
        NMConnection(True, ssid='my home network'),
        ]

    res = staffapp.get(reverse("server:wifi_history"), status=200)
    assert 'Wi-Fi hardware is disabled' not in res.unicode_body
    assert 'No known Wi-Fi networks' not in res.unicode_body
    assert 'my home network' in res.unicode_body
    assert 'random open network' in res.unicode_body


def test_staff_forgets_wifi_connection(mocker, staffapp):
    def delete_connection(connection):
        current = NMSettings.ListConnections()
        current = [c for c in current if c.ssid != connection.ssid]
        NMSettings.ListConnections.side_effect = lambda: current

    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(True, ssid='random open network', is_secure=False),
        NMConnection(
            True, ssid='my home network', delete_func=delete_connection),
        ]

    form = staffapp.get(reverse('server:wifi_history')).forms['wifi_history']
    form['my home network'].checked = True
    res = form.submit()

    assert res.status_int == 200
    assert 'Wi-Fi hardware is disabled' not in res.unicode_body
    assert 'No known Wi-Fi networks' not in res.unicode_body
    assert 'my home network' not in res.unicode_body
    assert 'random open network' in res.unicode_body


def test_staff_forgets_all_wifi_connections(mocker, staffapp):
    def delete_connection(connection):
        current = NMSettings.ListConnections()
        current = [c for c in current if c.ssid != connection.ssid]
        NMSettings.ListConnections.side_effect = lambda: current

    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(
            True, ssid='random open network', is_secure=False,
            delete_func=delete_connection),
        NMConnection(
            True, ssid='my home network', delete_func=delete_connection),
        ]

    form = staffapp.get(reverse('server:wifi_history')).forms['wifi_history']
    form['my home network'].checked = True
    form['random open network'].checked = True
    res = form.submit()

    assert res.status_int == 200
    assert 'No known Wi-Fi networks' in res.unicode_body
    assert 'my home network' not in res.unicode_body
    assert 'random open network' not in res.unicode_body


def test_staff_forgets_non_existing_connection(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: [
        NMConnection(False),
        NMConnection(True, ssid='random open network', is_secure=False),
        NMConnection(True, ssid='my home network'),
        ]

    name = 'no such network'
    form = staffapp.get(reverse('server:wifi_history')).forms['wifi_history']
    new_checkbox = Checkbox(form, 'input', name, None, True, id=name)
    form.fields[name] = new_checkbox
    form.field_order.append((name, new_checkbox))
    form.fields[name].checked = True
    res = form.submit()

    assert res.status_int == 200
    assert 'Wi-Fi hardware is disabled' not in res.unicode_body
    assert 'No known Wi-Fi networks' not in res.unicode_body
    assert 'my home network' in res.unicode_body
    assert 'random open network' in res.unicode_body


def test_staff_should_see_packages_with_cards(staffapp, systemuser, catalog):
    from ideascube.configuration import set_config
    from ideascube.serveradmin.catalog import Package
    set_config('home-page', 'displayed-package-ids', ['test.package1'], systemuser)

    catalog.add_mocked_package(Package('test.package1', {
        'name':'Test package1',
        'description':'Test package1 description',
        'language':'fr',
        'staff_only':False}))
    catalog.add_mocked_package(Package('test.package2', {
        'name':'Test package2',
        'description':'Test package2 description',
        'language':'fr',
        'staff_only':False}))
    catalog.add_mocked_package(Package('test.package3', {
        'name':'Test package3 no template',
        'description':'Test package3.\n'
                      'A package without template'}))

    res = staffapp.get(reverse("server:home_page"), status=200)
    form = res.forms['cards']
    inputs = form.fields['displayed']

    # We use the private attribute _value here cause the
    # value attribute is set to 'on' if the input is checked.
    # As we want to test the value set *in the html* we need to
    # use the real value, ie the _value attribute.
    # See https://github.com/Pylons/webtest/issues/165
    assert len(inputs) == 3
    assert inputs[0]._value == 'test.package1'
    assert inputs[0].checked
    assert inputs[1]._value == 'test.package2'
    assert not inputs[1].checked
    assert inputs[2]._value == 'test.package3'
    assert not inputs[2].checked

    # inverse the checked
    for input_ in form.fields['displayed']:
        input_.checked = not input_.checked

    res = form.submit()
    inputs = res.forms['cards'].fields['displayed']
    assert not inputs[0].checked
    assert inputs[1].checked
    assert inputs[2].checked


def test_staff_can_set_languages(staffapp):
    set_config('content', 'local-languages', ['en'], staffapp.user)

    response = staffapp.get(reverse('server:languages'))

    form = response.forms['languages']
    checked = sorted(f.id for f in form.fields['languages'] if f.checked)
    assert checked == ['en']

    for field in form.fields['languages']:
         field.checked = field.id in ('ar', 'zh-hant')

    response = form.submit()

    form = response.forms['languages']
    checked = sorted(f.id for f in form.fields['languages'] if f.checked)
    assert checked == ['ar', 'zh-hant']
    assert get_config('content', 'local-languages') == ['ar', 'zh-hant']


def test_staff_cannot_unset_all_languages(staffapp):
    set_config('content', 'local-languages', ['ar', 'zh-hant'], staffapp.user)

    response = staffapp.get(reverse('server:languages'))

    form = response.forms['languages']
    checked = sorted(f.id for f in form.fields['languages'] if f.checked)
    assert checked == ['ar', 'zh-hant']

    for field in form.fields['languages']:
         field.checked = False

    response = form.submit()

    assert 'Please select at least one language' in response.unicode_body
    form = response.forms['languages']
    checked = sorted(f.id for f in form.fields['languages'] if f.checked)
    assert checked == ['ar', 'zh-hant']
    assert get_config('content', 'local-languages') == ['ar', 'zh-hant']
