import os
import zipfile

import pytest
from webtest.forms import Checkbox, Upload
from mock import MagicMock
from mock import patch

from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile

from ..backup import Backup
from .test_backup import BACKUPS_ROOT, DATA_ROOT, BACKUPED_ROOT
from . import NMActiveConnection, NMConnection, NMDevice

pytestmark = pytest.mark.django_db


class FakePopen(object):
    def __init__(self, *args, **kwargs):
        self.returncode = 0

    def communicate(self):
        return "", ""

    def wait(self):
        pass


@pytest.mark.parametrize("page", [
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


def test_staff_user_should_access_services(monkeypatch, staffapp):
    monkeypatch.setattr("subprocess.Popen", FakePopen)
    assert staffapp.get(reverse("server:services"), status=200)


def test_should_override_service_action_caller(staffapp, settings):
    spy = MagicMock()
    settings.SERVICES = [{'name': 'xxxx', 'status_caller': spy}]
    assert staffapp.get(reverse("server:services"), status=200)
    assert spy.call_count == 1


def test_staff_user_should_access_power_admin(staffapp):
    assert staffapp.get(reverse("server:power"), status=200)


def test_staff_user_should_access_backup_admin(staffapp):
    assert staffapp.get(reverse("server:backup"), status=200)


def test_backup_should_list_available_backups(staffapp, backup):
    form = staffapp.get(reverse('server:backup')).forms['backup']
    radio_options = form.get('backup').options
    assert len(radio_options) == 4
    assert radio_options[3][0] == backup.name


def test_backup_button_should_save_a_new_backup(staffapp, monkeypatch,
                                                settings):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.FORMAT', 'zip')
    settings.BACKUPED_ROOT = BACKUPED_ROOT
    try:
        os.makedirs(BACKUPED_ROOT)
    except OSError:
        pass
    filename = 'edoardo-0.0.0-201501231405.zip'
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
    assert zipfile.is_zipfile(filepath)
    archive = zipfile.ZipFile(filepath)
    assert 'backup.me' in archive.namelist()
    os.remove(filepath)
    os.remove(proof_file)


def test_restore_button_should_restore(staffapp, monkeypatch, settings,
                                       backup):
    assert len(os.listdir(DATA_ROOT)) == 4  # One by format.
    TEST_BACKUPED_ROOT = 'ideascube/serveradmin/tests/backuped'
    settings.BACKUPED_ROOT = TEST_BACKUPED_ROOT
    dbpath = os.path.join(TEST_BACKUPED_ROOT, 'default.sqlite')
    assert not os.path.exists(dbpath)
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['backup'] = backup.name
    form.submit('do_restore')
    assert len(os.listdir(DATA_ROOT)) == 4
    assert os.path.exists(dbpath)
    os.remove(dbpath)


def test_download_button_should_download_zip_file(staffapp, backup):
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['backup'] = backup.name
    resp = form.submit('do_download')
    assert backup.name in resp['Content-Disposition']
    assert zipfile.is_zipfile(ContentFile(resp.content))


def test_delete_button_should_remove_file(staffapp, backup):
    assert len(os.listdir(DATA_ROOT)) == 4
    with open(backup.path, mode='rb') as f:
        other = Backup.load(ContentFile(f.read(),
                            name='kavumu-0.1.0-201401241620.zip'))
    assert len(os.listdir(DATA_ROOT)) == 5
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['backup'] = other.name
    form.submit('do_delete')
    assert len(os.listdir(DATA_ROOT)) == 4


def test_upload_button_create_new_backup_with_uploaded_file(staffapp,
                                                            monkeypatch):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    backup_name = 'musasa-0.1.0-201501241620.zip'
    backup_path = os.path.join(BACKUPS_ROOT, backup_name)
    assert not os.path.exists(backup_path)
    with open(os.path.join(DATA_ROOT, backup_name), mode='rb') as f:
        form = staffapp.get(reverse('server:backup')).forms['backup']
        form['upload'] = Upload(backup_name, f.read())
        form.submit('do_upload')
        assert os.path.exists(backup_path)
        os.remove(backup_path)


def test_upload_button_do_not_create_backup_with_non_zip_file(staffapp,
                                                              monkeypatch):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    backup_name = 'musasa-0.1.0-201501241620.zip'
    backup_path = os.path.join(BACKUPS_ROOT, backup_name)
    assert not os.path.exists(backup_path)
    form = staffapp.get(reverse('server:backup')).forms['backup']
    form['upload'] = Upload(backup_name, 'xxx')
    resp = form.submit('do_upload')
    assert resp.status_code == 200
    assert not os.path.exists(backup_path)


def test_upload_button_do_not_create_backup_with_bad_file_name(staffapp,
                                                               monkeypatch):
    monkeypatch.setattr('ideascube.serveradmin.backup.Backup.ROOT',
                        BACKUPS_ROOT)
    backup_name = 'musasa-0.1.0-201501241620.zip'
    backup_path = os.path.join(BACKUPS_ROOT, backup_name)
    assert not os.path.exists(backup_path)
    with open(os.path.join(DATA_ROOT, backup_name), mode='rb') as f:
        form = staffapp.get(reverse('server:backup')).forms['backup']
        form['upload'] = Upload('badname.zip', f.read())
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
    assert u'Wi-Fi hardware is disabled' in res.unicode_body
    assert u'No Wi-Fi available' in res.unicode_body


def test_staff_lists_wifi_networks(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.Devices = [NMDevice(True)]
    NM.WirelessHardwareEnabled = True

    NMSettings = mocker.patch('ideascube.serveradmin.wifi.NMSettings')
    NMSettings.ListConnections.side_effect = lambda: []

    res = staffapp.get(reverse("server:wifi"), status=200)
    assert u'Wi-Fi hardware is disabled' not in res.unicode_body
    assert u'Wi-Fi is disabled' not in res.unicode_body
    assert u'No Wi-Fi available' not in res.unicode_body
    assert u'my home network' in res.unicode_body
    assert u'random open network' in res.unicode_body


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
    assert u'No Wi-Fi available' not in res.unicode_body
    assert u"Connected to random open network" in res.unicode_body


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
    assert u'No Wi-Fi available' not in res.unicode_body
    assert u"Connected to random open network" in res.unicode_body
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
    assert u'No Wi-Fi available' not in res.unicode_body
    assert u"Connected to my home network" in res.unicode_body


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
    assert u'A key is required to connect to this network' in res.unicode_body
    assert NMSettings.AddConnection.call_count == 0

    res = staffapp.post(reverse(
        "server:wifi", kwargs={'ssid': 'my home network'}),
        params={
            'wifi_key': 'some wifi key',
            'csrfmiddlewaretoken': staffapp.cookies['csrftoken'],
            },
        status=200)
    assert u"Connected to my home network" in res.unicode_body
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
    assert u'No Wi-Fi available' not in res.unicode_body
    assert u"No such network: no such network" in res.unicode_body


def test_staff_accesses_wifi_history_without_wireless(mocker, staffapp):
    NM = mocker.patch('ideascube.serveradmin.wifi.NetworkManager')
    NM.WirelessHardwareEnabled = False

    res = staffapp.get(reverse("server:wifi_history"), status=200)
    print(res.unicode_body)
    assert u'Wi-Fi hardware is disabled' in res.unicode_body
    assert u'No known Wi-Fi networks' in res.unicode_body


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
    assert u'Wi-Fi hardware is disabled' not in res.unicode_body
    assert u'No known Wi-Fi networks' not in res.unicode_body
    assert u'my home network' in res.unicode_body
    assert u'random open network' in res.unicode_body


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
    assert u'Wi-Fi hardware is disabled' not in res.unicode_body
    assert u'No known Wi-Fi networks' not in res.unicode_body
    assert u'my home network' not in res.unicode_body
    assert u'random open network' in res.unicode_body


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
    assert u'No known Wi-Fi networks' in res.unicode_body
    assert u'my home network' not in res.unicode_body
    assert u'random open network' not in res.unicode_body


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
    assert u'Wi-Fi hardware is disabled' not in res.unicode_body
    assert u'No known Wi-Fi networks' not in res.unicode_body
    assert u'my home network' in res.unicode_body
    assert u'random open network' in res.unicode_body


def test_wpa_config(staffapp, wpa_config):
    resp = staffapp.get(reverse('server:wpa_config'))
    form = resp.forms['wpa_config']
    assert form['enable'].checked is True
    assert form['passphrase'].value == 'pwa'

    form['passphrase'] = 'newsecret'
    resp = form.submit()
    resp = resp.follow()

    resp.mustcontain('Hotspot is now enabled with passphrase newsecret.')
    form = resp.forms['wpa_config']
    assert form['enable'].checked is True
    assert form['passphrase'].value == 'newsecret'
    form['enable'] = False
    resp = form.submit()
    resp = resp.follow()

    resp.mustcontain('Hotspot is now disabled.')
    form = resp.forms['wpa_config']
    assert form['enable'].checked is False
    assert form['passphrase'].value == 'newsecret'


def test_wpa_config_file_missing(staffapp, wpa_config):
    wpa_config.__class__.configfile = '/xyz/missing'
    resp = staffapp.get(reverse('server:wpa_config'))
    resp.mustcontain('Hotspot configuration not found.')


def test_wpa_config_password_required(staffapp, wpa_config):
    resp = staffapp.get(reverse('server:wpa_config'))
    form = resp.forms['wpa_config']
    form['passphrase'] = ''
    resp = form.submit()
    resp.mustcontain('This field is required.')


def test_wpa_config_file_not_writeable(staffapp, wpa_config):
    resp = staffapp.get(reverse('server:wpa_config'))
    form = resp.forms['wpa_config']
    patcher = patch('ideascube.serveradmin.views.WPAConfig.save',
                    side_effect=IOError('Permission denied'))
    patcher.start()
    resp = form.submit().follow()
    resp.mustcontain('We are not able to change hotspot configuration.')
    patcher.stop()
