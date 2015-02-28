import pytest

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import RequestFactory

from ideasbox.views import validate_url

pytestmark = pytest.mark.django_db
user_model = get_user_model()


def test_home_page(app):
    assert app.get('/')


def test_anonymous_user_should_not_access_admin(app):
    response = app.get(reverse('admin:index'), status=302)
    assert 'login' in response['Location']


def test_normal_user_should_not_access_admin(loggedapp, user):
    response = loggedapp.get(reverse('admin:index'), status=302)
    assert 'login' in response['Location']


def test_staff_user_should_access_admin(staffapp):
    assert staffapp.get(reverse('admin:index'), status=200)


def test_login_page_should_return_form_in_GET_mode(app):
    assert app.get(reverse('login'), status=200)


def test_login_page_should_log_in_user_if_POST_data_is_correct(client, user):
    response = client.post(reverse('login'), {
        'username': user.serial,
        'password': 'password'
    }, follow=True)
    assert response.status_code == 200
    assert len(response.redirect_chain) == 1
    assert response.context['user'].is_authenticated()


def test_login_page_should_not_log_in_user_with_incorrect_POST(client, user):
    response = client.post(reverse('login'), {
        'username': user.serial,
        'password': 'passwordxxx'
    }, follow=True)
    assert response.status_code == 200
    assert len(response.redirect_chain) == 0
    assert not response.context['user'].is_authenticated()


def test_user_list_page_should_be_accessible(app, user):
    response = app.get(reverse('user_list'))
    response.mustcontain(unicode(user))


def test_user_detail_page_should_be_accessible(app, user):
    response = app.get(reverse('user_detail', kwargs={'pk': user.pk}))
    response.mustcontain(unicode(user))


def test_user_create_page_should_not_be_accessible_to_anonymous(app):
    assert app.get(reverse('user_create'), status=302)


def test_non_staff_should_not_access_user_create_page(loggedapp, user):
    assert loggedapp.get(reverse('user_create'), status=302)


def test_user_create_page_should_be_accessible_to_staff(staffapp):
    assert staffapp.get(reverse('user_create'), status=200)


def test_should_create_user_with_serial_only(staffapp):
    assert len(user_model.objects.all()) == 1
    serial = '12345xz22'
    form = staffapp.get(reverse('user_create')).forms['model_form']
    form['serial'] = serial
    form.submit()
    assert len(user_model.objects.all()) == 2
    assert user_model.objects.filter(serial=serial)


def test_should_not_create_user_without_serial(staffapp):
    assert len(user_model.objects.all()) == 1
    form = staffapp.get(reverse('user_create')).forms['model_form']
    form.submit()
    assert len(user_model.objects.all()) == 1


def test_user_update_page_should_not_be_accessible_to_anonymous(app, user):
    assert app.get(reverse('user_update', kwargs={'pk': user.pk}), status=302)


def test_non_staff_should_not_access_user_update_page(loggedapp, user):
    assert loggedapp.get(reverse('user_update', kwargs={'pk': user.pk}),
                         status=302)


def test_staff_should_access_user_update_page(staffapp, user):
    assert staffapp.get(reverse('user_update', kwargs={'pk': user.pk}),
                        status=200)


def test_staff_should_be_able_to_update_user(staffapp, user):
    assert len(user_model.objects.all()) == 2
    url = reverse('user_update', kwargs={'pk': user.pk})
    short_name = 'Denis'
    form = staffapp.get(url).forms['model_form']
    form['serial'] = user.serial
    form['short_name'] = short_name
    form.submit().follow()
    assert len(user_model.objects.all()) == 2
    assert user_model.objects.get(serial=user.serial).short_name == short_name


def test_should_not_update_user_without_serial(app, staffapp, user):
    url = reverse('user_update', kwargs={'pk': user.pk})
    form = staffapp.get(url).forms['model_form']
    form['serial'] = ''
    form['short_name'] = 'ABCDEF'
    assert form.submit()
    dbuser = user_model.objects.get(serial=user.serial)
    assert dbuser.short_name == user.short_name


def test_delete_page_should_not_be_reachable_to_anonymous(app, user):
    assert app.get(reverse('user_delete', kwargs={'pk': user.pk}), status=302)


def test_delete_page_should_not_be_reachable_to_non_staff(loggedapp, user):
    assert loggedapp.get(reverse('user_delete', kwargs={'pk': user.pk}),
                         status=302)


def test_staff_user_should_access_confirm_delete_page(staffapp, user):
    assert staffapp.get(reverse('user_delete', kwargs={'pk': user.pk}),
                        status=200)


def test_anonymous_cannot_delete_user(app, user):
    assert len(user_model.objects.all()) == 1
    url = reverse('user_delete', kwargs={'pk': user.pk})
    url = reverse('user_delete', kwargs={'pk': user.pk})
    assert app.get(url, status=302)
    assert len(user_model.objects.all()) == 1


def test_non_staff_cannot_delete_user(loggedapp, user):
    assert len(user_model.objects.all()) == 1
    url = reverse('user_delete', kwargs={'pk': user.pk})
    assert loggedapp.get(url, status=302)
    assert len(user_model.objects.all()) == 1


def test_staff_user_can_delete_user(staffapp, user):
    assert len(user_model.objects.all()) == 2  # staff user and normal user
    url = reverse('user_delete', kwargs={'pk': user.pk})
    form = staffapp.get(url).forms['delete_form']
    form.submit()
    assert len(user_model.objects.all()) == 1


def build_request(target="http://example.org", verb="get", **kwargs):
    defaults = {
        'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
        'HTTP_REFERER': 'http://testserver/path/'
    }
    defaults.update(kwargs)
    func = getattr(RequestFactory(**defaults), verb)
    return func('/', {'url': target})


def test_good_request_passes():
    target = "http://osm.org/georss.xml"
    request = build_request(target)
    url = validate_url(request)
    assert url == target


def test_no_url_raises():
    with pytest.raises(AssertionError):
        validate_url(build_request(""))


def test_relative_url_raises():
    with pytest.raises(AssertionError):
        validate_url(build_request("/just/a/path/"))


def test_file_uri_raises():
    with pytest.raises(AssertionError):
        validate_url(build_request("file:///etc/passwd"))


def test_localhost_raises():
    with pytest.raises(AssertionError):
        validate_url(build_request("http://localhost/path/"))


def test_POST_raises():
    with pytest.raises(AssertionError):
        validate_url(build_request(verb="post"))


def test_unkown_domain_raises():
    with pytest.raises(AssertionError):
        validate_url(build_request("http://xlkjdkjsdlkjfd.com"))


def test_valid_proxy_request(app):
    url = reverse('ajax-proxy')
    params = {'url': 'http://example.org'}
    headers = {
        'X_REQUESTED_WITH': 'XMLHttpRequest',
        'REFERER': 'http://testserver'
    }
    environ = {'SERVER_NAME': 'testserver'}
    response = app.get(url, params, headers, environ)
    assert response.status_code == 200
    assert 'Example Domain' in response.content
    assert "Vary" not in response.headers
