from subprocess import call

import batinfo
import os
import requests
from django.conf import settings
from django.contrib import messages
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect
from django.utils.translation import ugettext as _
from kinto_client import Client

from ideascube.decorators import staff_member_required

from .backup import Backup
from .systemd import Manager, NoSuchUnit, UnitManagementError
from .wifi import (
    AvailableWifiNetwork, KnownWifiConnection, enable_wifi, WifiError)


@staff_member_required
def services(request):
    services = settings.SERVICES
    manager = Manager()
    to_manage = request.POST.get('name')

    for service in services:
        # Reset these, otherwise the values are cached from a previous run.
        service['status'] = False
        service['error'] = None

        name = service['name']

        try:
            service_unit = manager.get_service(service['name'])

            if name == to_manage:
                if 'start' in request.POST:
                    manager.activate(service_unit.Id)

                elif 'stop' in request.POST:
                    manager.deactivate(service_unit.Id)

                elif 'restart' in request.POST:
                    manager.restart(service_unit.Id)

            service['status'] = service_unit.active

        except NoSuchUnit:
            service['error'] = 'Not installed'

        except UnitManagementError as e:
            messages.error(request, e)

    return render(
        request, 'serveradmin/services.html', {'services': services})


@staff_member_required
def power(request):
    if request.POST:
        if 'stop' in request.POST:
            call(["sudo", "poweroff"])
        elif 'restart' in request.POST:
            call(["sudo", "reboot"])

    return render(request, 'serveradmin/power.html')


@staff_member_required
def backup(request):
    if request.POST:
        if 'do_create' in request.POST:
            backup = Backup.create()
            msg = _('Succesfully created backup {filename}').format(
                filename=backup.name
            )
            messages.add_message(request, messages.SUCCESS, msg)
        elif 'do_upload' in request.POST:
            if 'upload' in request.FILES:
                file_ = request.FILES['upload']
                try:
                    backup = Backup.load(file_)
                except Exception as e:
                    msg = _('Unable to load file:')
                    msg = "{msg} {error}".format(msg=msg, error=str(e))
                    messages.add_message(request, messages.ERROR, msg)
                else:
                    msg = _('File {name} has been loaded.').format(
                        name=backup.name)
                    messages.add_message(request, messages.SUCCESS, msg)
            else:
                messages.add_message(request, messages.ERROR,
                                     _('No file found to upload.'))
        elif 'backup' in request.POST:
            backup = Backup(request.POST['backup'])
            msg = None
            if 'do_delete' in request.POST:
                backup.delete()
                msg = _('Succesfully deleted backup {filename}').format(
                    filename=backup.name
                )
            elif 'do_restore' in request.POST:
                backup.restore()
                msg = _('Succesfully restored backup {filename}').format(
                    filename=backup.name
                )
            elif 'do_download' in request.POST:
                response = StreamingHttpResponse(open(backup.path, 'rb'))
                cd = 'attachment; filename="{name}"'.format(name=backup.name)
                response['Content-Disposition'] = cd
                return response
            if msg:
                messages.add_message(request, messages.SUCCESS, msg)
    context = {
        'backups': Backup.list()
    }
    return render(request, 'serveradmin/backup.html', context)


@staff_member_required
def battery(request):
    return render(request, 'serveradmin/battery.html',
                  {'batteries': batinfo.batteries()})


@staff_member_required
def wifi(request, ssid=''):
    try:
        enable_wifi()
        wifi_list = AvailableWifiNetwork.all()

    except WifiError as e:
        messages.error(request, e)
        return render(request, 'serveradmin/wifi.html')

    if ssid:
        try:
            network = wifi_list[ssid]
            wifi_key = request.POST.get('wifi_key', '')
            network.connect(wifi_key=wifi_key)
            messages.success(
                request, _('Connected to {ssid}').format(ssid=ssid))

        except KeyError:
            messages.error(
                request, _('No such network: {ssid}').format(ssid=ssid))

        except WifiError as e:
            messages.error(request, e)

    return render(
        request, 'serveradmin/wifi.html', {'wifi_list': wifi_list.values()})


@staff_member_required
def wifi_history(request):
    try:
        enable_wifi()
        wifi_list = KnownWifiConnection.all()

    except WifiError as e:
        messages.error(request, e)
        return render(request, 'serveradmin/wifi_history.html')

    for ssid, checked in request.POST.items():
        if checked.lower() in ('on', 'true'):
            try:
                connection = wifi_list.pop(ssid)
                connection.forget()

            except KeyError:
                # Someone tried to forget a connection we don't know.
                continue

    return render(
        request, 'serveradmin/wifi_history.html',
        {'wifi_list': wifi_list.values()})


@staff_member_required
def packages(request):
    # XXX: Should have a local Kinto cache.
    client = Client(server_url='http://kinto.bsf-intranet.org/v1',
                    bucket='ideascube', collection='packages')
    packages = client.get_records()

    return render(
        request, 'serveradmin/packages.html',
        {'packages': packages})


@staff_member_required
def package_detail(request, package_id):
    client = Client(server_url='http://kinto.bsf-intranet.org/v1',
                    bucket='ideascube', collection='packages')
    # XXX: Should use the local Kinto cache.
    package = client.get_record(package_id)

    # XXX: Should be done asynchroneously.
    def download_file(url, path=None):
        local_filename = url.split('/')[-1]

        if path:
            local_filename = os.path.join(path, local_filename)
        # NOTE the stream=True parameter
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        return local_filename

    download_file(package['data']['url'], '/tmp')

    return redirect('library:index')
