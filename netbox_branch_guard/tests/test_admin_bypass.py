"""
Reproduces the Admin/password bug: editing a model that netbox_branching has
permanently excluded from branching (users.User, core.*, extras.customfield, ...)
always writes directly to Main - there is no branch-local copy for the write to
route into, whether or not a branch is "active" in the cookie/session.

Before this fix the guard only accounted for this in the no-branch (Main) path.
With a branch active, it fell through to the ownership check and allowed the
request - which looked safe (branch-scoped) but wasn't: the write still landed
in Main, silently, with no block message to warn anyone it bypassed the
"changes must go through a branch" workflow entirely.

The fix adds the same exemption - via supports_branching() - to the model_exempt
check in both code paths. These tests stub netbox_branching.utilities.supports_branching
directly (the real package isn't installed in this standalone test harness - see
conftest.py) rather than a real Branch model, since the branch-active bypass must
fire before the middleware ever looks up a Branch.
"""
import sys
import types

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


def _prepare(request, branch_id=None):
    from django.contrib.messages.storage.fallback import FallbackStorage

    request.user = FakeUser()
    request.session = {}
    request._messages = FallbackStorage(request)
    if branch_id:
        request.COOKIES["active_branch"] = branch_id
    return request


def _allowed(request):
    middleware = NetboxBranchGuardMiddleware(lambda r: SENTINEL)
    return middleware(request) is SENTINEL


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    Interface.objects.all().delete()


@pytest.fixture
def stub_supports_branching(monkeypatch):
    """
    Installs a fake netbox_branching.utilities module whose supports_branching()
    is controlled by the test, and removes it again afterwards.
    """
    def _install(return_value):
        fake_pkg = types.ModuleType("netbox_branching")
        fake_utils = types.ModuleType("netbox_branching.utilities")
        fake_utils.supports_branching = lambda model: return_value
        fake_pkg.utilities = fake_utils
        monkeypatch.setitem(sys.modules, "netbox_branching", fake_pkg)
        monkeypatch.setitem(sys.modules, "netbox_branching.utilities", fake_utils)

    return _install


def test_non_branchable_model_bypasses_guard_on_main(stub_supports_branching):
    stub_supports_branching(False)
    iface = Interface.objects.create(name="eth0", status="active", description="d")

    request = _prepare(factory.post(f"/interfaces/{iface.pk}/edit/", data={
        "name": "renamed",  # 'name' isn't in excluded_fields - would normally block
    }))

    assert _allowed(request)


def test_non_branchable_model_bypasses_guard_with_branch_active(stub_supports_branching):
    stub_supports_branching(False)
    iface = Interface.objects.create(name="eth0", status="active", description="d")

    # No real Branch exists for this schema_id - if the bypass didn't fire before
    # the Branch lookup, this would error out instead of allowing the request.
    request = _prepare(
        factory.post(f"/interfaces/{iface.pk}/edit/", data={"name": "renamed"}),
        branch_id="nonexistent-branch",
    )

    assert _allowed(request)


def test_branchable_model_is_still_blocked_on_main(stub_supports_branching):
    stub_supports_branching(True)
    iface = Interface.objects.create(name="eth0", status="active", description="d")

    request = _prepare(factory.post(f"/interfaces/{iface.pk}/edit/", data={
        "name": "renamed",  # 'name' isn't in excluded_fields
    }))

    assert not _allowed(request)


def test_branchable_model_without_netbox_branching_installed_keeps_old_behavior():
    # No stub installed at all: _model_opts_out_of_branching() must fail closed
    # (no bypass) when netbox_branching isn't importable, exactly as it did before
    # this fix existed.
    iface = Interface.objects.create(name="eth0", status="active", description="d")

    request = _prepare(factory.post(f"/interfaces/{iface.pk}/edit/", data={
        "name": "renamed",
    }))

    assert not _allowed(request)
