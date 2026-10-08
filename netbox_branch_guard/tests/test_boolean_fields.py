"""
Reproduces a false-positive block: saving an edit form that leaves a
BooleanField checkbox checked (e.g. Interface.enabled=True, unchanged) got
reported as a real change, because the submitted literal "on" never
matched Python's True via the generic string normalization - so every
save of an object with a checked, non-excluded boolean field was blocked
on Main even when nothing was actually edited.
"""
import pytest
from django.test import RequestFactory

from netbox_branch_guard.middleware import NetboxBranchGuardMiddleware
from netbox_branch_guard.tests.testapp.models import Interface

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
    from django.contrib.messages.storage.fallback import FallbackStorage

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
    Interface.objects.all().delete()


def test_resubmitting_checked_boolean_unchanged_is_allowed():
    iface = Interface.objects.create(name="eth0", enabled=True, status="active", description="d")

    request = _prepare(factory.post(f"/interfaces/{iface.pk}/edit/", data={
        "enabled": "on",  # checkbox stayed checked, nothing actually changed
        "status": iface.status,
        "description": iface.description,
    }))

    assert _allowed(request)


def test_actually_checking_boolean_is_still_blocked():
    iface = Interface.objects.create(name="eth0", enabled=False, status="active", description="d")

    request = _prepare(factory.post(f"/interfaces/{iface.pk}/edit/", data={
        "enabled": "on",  # real change: False -> True
        "status": iface.status,
        "description": iface.description,
    }))

    assert not _allowed(request)
