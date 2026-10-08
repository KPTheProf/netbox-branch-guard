"""
Reproduces the delete-bypass bug: once `excluded_fields` is non-empty, a
DELETE/delete-confirmation request carries no field values to compare
against the DB (there's nothing being "changed"), so the old code found
zero non-exempt field changes and wrongly treated that as "only excluded
fields were touched" -> the whole object got deleted on Main anyway.
"""
import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponseRedirect
from django.test import RequestFactory

from netbox_branch_guard.middleware import NetboxBranchGuardMiddleware
from netbox_branch_guard.tests.testapp.models import Device

pytestmark = pytest.mark.django_db

factory = RequestFactory()
SENTINEL = object()


class FakeUser:
    is_authenticated = True
    is_superuser = False

    class groups:
        @staticmethod
        def all():
            return []

    def __str__(self):
        return "fakeuser"


def _prepare(request):
    request.user = FakeUser()
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def _allowed(request):
    middleware = NetboxBranchGuardMiddleware(lambda r: SENTINEL)
    return middleware(request) is SENTINEL


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    Device.objects.all().delete()


def test_single_object_delete_on_main_is_blocked():
    d1 = Device.objects.create(name="d1")

    request = _prepare(factory.post(f"/devices/{d1.pk}/delete/", data={"confirm": "True"}))

    assert not _allowed(request)
    assert Device.objects.filter(pk=d1.pk).exists()


def test_bulk_delete_on_main_is_blocked():
    d1 = Device.objects.create(name="d1")
    d2 = Device.objects.create(name="d2")

    request = _prepare(factory.post("/devices/delete/", data={
        "pk": [str(d1.pk), str(d2.pk)],
        "confirm": "True",
    }))

    assert not _allowed(request)


def test_api_delete_method_on_main_is_blocked():
    d1 = Device.objects.create(name="d1")

    request = _prepare(factory.generic("DELETE", f"/devices/{d1.pk}/delete/"))

    assert not _allowed(request)


def test_delete_blocked_response_is_a_redirect():
    d1 = Device.objects.create(name="d1")

    request = _prepare(factory.post(f"/devices/{d1.pk}/delete/", data={"confirm": "True"}))

    middleware = NetboxBranchGuardMiddleware(lambda r: SENTINEL)
    response = middleware(request)
    assert isinstance(response, HttpResponseRedirect)


def test_edit_of_only_excluded_fields_is_still_allowed():
    # Make sure the delete-detection doesn't collaterally block real edits.
    d1 = Device.objects.create(name="d1", status="planned", platform="cisco", description="d")

    request = _prepare(factory.post(f"/devices/{d1.pk}/edit/", data={
        "status": "active",
        "platform": d1.platform,
        "description": d1.description,
    }))

    assert _allowed(request)
