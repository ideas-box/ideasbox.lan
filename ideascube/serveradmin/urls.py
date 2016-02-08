from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^power/$', views.power, name='power'),
    url(r'^services/$', views.services, name='services'),
    url(r'^backup/$', views.backup, name='backup'),
    url(r'^battery/$', views.battery, name='battery'),
    url(r'^wifi/(?P<ssid>.+)?$', views.wifi, name='wifi'),
    url(r'^wifi_history/$', views.wifi_history, name='wifi_history'),
    url(r'^catalog/$', views.catalog, name='catalog'),
    url(r'^catalog/install/(?P<id>.+)?$', views.install_package,
        name='install_package'),
]
