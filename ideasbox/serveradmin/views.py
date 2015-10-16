from subprocess import call

import batinfo
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _

from wifi import Cell, Scheme
from wifi.exceptions import ConnectionError, InterfaceError

from .backup import Backup
from .utils import call_service

interface = 'wlan0'

@staff_member_required
def services(request):
    services = settings.SERVICES
    service_action = 'status'
    if request.POST:
        active_service = request.POST['name']
        if 'start' in request.POST:
            service_action = 'start'
        elif 'stop' in request.POST:
            service_action = 'stop'
        elif 'restart' in request.POST:
            service_action = 'restart'
    else:
        active_service = None

    for service in services:
        if active_service == service['name']:
            service['action'] = service_action
        else:
            service['action'] = 'status'
        # The way to run the action may be overrided in the service definition
        # in the settings.
        caller = '{action}_caller'.format(**service)
        if caller in service:
            status = service[caller](service)
        else:
            status = call_service(service)
        service['error'] = status.get('error')
        service['status'] = status.get('status')
    return render(request, 'serveradmin/services.html', {'services': services})


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
                    msg = "{msg} {error}".format(msg=msg, error=e.message)
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


unset_config_data = """scheme_current=None
interface_current={interface}
scheme_active=False
""".format(interface=interface)

def set_wifilist():
    from wifi.utils import get_property, set_properties
    f = open('.runningconfig', 'r+')
    read_data = f.read()
    if len(read_data) == 0:
        f.write(unset_config_data)
    f.close()
    to_bool = {'True' : True, 'False' : False, None : False, 'None' : False}
    # reset scheme_active property
    essid = get_property('scheme_current')
    try:
        is_essid = to_bool[essid]
    except KeyError:
        is_essid = True
        essid = essid.split('--')[0]
    if is_essid:
        options = {'wireless-essid' : essid}
    else:
        options = None
    set_properties(None, None, config=options)
    is_connected = to_bool[get_property('scheme_active')]
    action = {True : _('Disconnect'), False : _('Connect')}
    try:
        wifi = Cell.all(interface, sudo=True)
        # Florian --> config file with interface name
    except InterfaceError:
        wifi = ""
    for hotspot in wifi:
            # find out if connected with
            id_ = '--'.join([hotspot.ssid, hotspot.address])
            hotspot.is_active = (get_property('scheme_current') == id_)
            hotspot.is_connected = (hotspot.is_active and is_connected)
            hotspot.action = action[hotspot.is_connected]
    return wifi, is_connected


@staff_member_required
def wifi(request):
    set_wifilist()
    if request.POST:
        action = request.POST['action']
        if action == _('Connect'):
            # we use the addresses to set unicity of the schemes created
            address = request.POST['address']
            ssid = request.POST['ssid']
            cell_kwargs = {'interface' : interface,
                           'name' : '--'.join([ssid, address]),
                           'passkey' : request.POST['key']}
            cell = Cell.where(cell_kwargs['interface'],
                              lambda cell: cell.address == address)[0]
            cell_kwargs['cell'] = cell
            scheme = Scheme.for_cell(**cell_kwargs)
            if not Scheme.find(cell_kwargs['interface'], scheme.name):
                scheme.save()
            try:
                scheme.activate()
            except ConnectionError:
                # just to verify in terminal
                print "Connection Error"
        else:
            # disconnect
            import subprocess
            # to avoid errors in tests
            subprocess.call(["/sbin/ifdown", interface])
    # refresh wifilist
    wifilist, status = set_wifilist()
    # causes the long load time because of the scan
    return render(request, 'serveradmin/wifi.html',
                  {'wifiList': wifilist,
                   'connection_status' : status})
