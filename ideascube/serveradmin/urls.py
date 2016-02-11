from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^power/$', views.power, name='power'),
    url(r'^services/$', views.services, name='services'),
    url(r'^backup/$', views.backup, name='backup'),
    url(r'^battery/$', views.battery, name='battery'),
    url(r'^wifi/(?P<ssid>.+)?$', views.wifi, name='wifi'),
    url(r'^wifi_history/$', views.wifi_history, name='wifi_history'),
    url(r'^packages/$', views.packages, name='packages'),
    url(r'^packages/(?P<package_id>.+)?$', views.package_detail,
        name='package_detail'),
]
