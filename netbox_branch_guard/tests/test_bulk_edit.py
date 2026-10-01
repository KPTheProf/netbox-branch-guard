"""
Reproduces the bulk/multiselect-edit bug: NetBox's BulkEditView POSTs every
form field, leaving untouched ones blank (meaning "don't change") and only
flags real edits via its own `_nullify` list. The middleware used to compare
every submitted value -- including those blanks -- against the object's
current DB value, so any non-excluded field with a non-blank DB value looked
"changed" and the whole bulk edit got blocked.
"""
import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponseRedirect
from django.test import RequestFactory

from netbox_branch_guard.middleware import NetboxBranchGuardMiddleware
from netbox_branch_guard.tests.testapp.models import Device

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


def test_bulk_edit_only_excluded_field_changed_is_allowed():
    d1 = Device.objects.create(name="d1", status="planned", description="old 1", platform="cisco")
    d2 = Device.objects.create(name="d2", status="planned", description="old 2", platform="juniper")

    request = _prepare(factory.post("/devices/edit/", data={
        "pk": [str(d1.pk), str(d2.pk)],
        "status": "active",   # excluded field, actually changed
        "description": "",    # untouched bulk-edit field, left blank
        "platform": "",       # untouched bulk-edit field, left blank
    }))

    assert _allowed(request)


def test_bulk_edit_real_change_to_non_excluded_field_is_blocked():
    d1 = Device.objects.create(name="d1", platform="cisco")
    d2 = Device.objects.create(name="d2", platform="juniper")

    request = _prepare(factory.post("/devices/edit/", data={
        "pk": [str(d1.pk), str(d2.pk)],
        "platform": "arista",  # real change, not excluded
        "status": "",
        "description": "",
    }))

    assert not _allowed(request)


def test_bulk_edit_explicit_nullify_of_non_excluded_field_is_blocked():
    d1 = Device.objects.create(name="d1", platform="cisco")

    request = _prepare(factory.post("/devices/edit/", data={
        "pk": [str(d1.pk)],
        "platform": "",
        "_nullify": ["platform"],  # user explicitly checked "clear this field"
        "status": "",
        "description": "",
    }))

    assert not _allowed(request)


def test_single_edit_clearing_non_excluded_field_is_still_blocked():
    d1 = Device.objects.create(name="d1", platform="cisco", status="active", description="d")

    request = _prepare(factory.post(f"/devices/{d1.pk}/edit/", data={
        "platform": "",  # single-edit form: blank really means "clear it"
        "status": d1.status,
        "description": d1.description,
    }))

    assert not _allowed(request)


def test_single_edit_only_excluded_field_changed_is_allowed():
    d1 = Device.objects.create(name="d1", status="planned", platform="cisco", description="d")

    request = _prepare(factory.post(f"/devices/{d1.pk}/edit/", data={
        "status": "active",
        "platform": d1.platform,
        "description": d1.description,
    }))

    assert _allowed(request)


def test_bulk_edit_blocked_response_is_a_redirect():
    d1 = Device.objects.create(name="d1", platform="cisco")

    request = _prepare(factory.post("/devices/edit/", data={
        "pk": [str(d1.pk)],
        "platform": "arista",
        "status": "",
        "description": "",
    }))

    middleware = NetboxBranchGuardMiddleware(lambda r: SENTINEL)
    response = middleware(request)
    assert isinstance(response, HttpResponseRedirect)
