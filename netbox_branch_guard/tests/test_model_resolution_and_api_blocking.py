"""
Covers two bugs found via a real vprod repro (PATCH /api/users/config/ - the
"Configure Table" column-preferences endpoint):

1. UserConfigViewSet exposes no queryset/model attribute (get_queryset() is a
   method, not a class attribute _resolve_model() can introspect), so the guard
   could never determine a model for it and treated "model unresolved" the same
   as "model is branchable and not exempt" - blocking it outright. In practice
   every write that actually needs branch enforcement goes through a
   NetBox-generated view backed by a queryset, which _resolve_model() already
   handles; a write with no resolvable model at all is something else entirely
   (a config/preference endpoint, a custom action, ...), not a branchable write
   hiding from us. The fix fails open in that case instead of requiring every
   such view to be hand-registered in view_model_map just to keep working.

2. The block response for Main-write violations always redirected via
   HTTP_REFERER, even for /api/ requests. Browsers preserve the HTTP method on
   301/302/307/308 redirects (per the fetch spec), so a blocked PATCH to an API
   endpoint got resent as a PATCH to the Referer page - typically a GET-only UI
   view - producing a confusing 405 instead of a response an API client could
   handle. The fix returns a JSON 403 for /api/ paths instead.

ConfigLikeView (testapp) mirrors UserConfigViewSet's shape: no queryset/model
attribute, not present in view_model_map.
"""
import json

import pytest
from django.test import RequestFactory

from netbox_branch_guard.middleware import NetboxBranchGuardMiddleware
from netbox_branch_guard.tests.testapp.models import Interface
from netbox_branch_guard.tests.test_admin_bypass import FakeUser, _prepare, stub_supports_branching  # noqa: F401

pytestmark = pytest.mark.django_db

factory = RequestFactory()
SENTINEL = object()


def _call(request, api_bypass=True):
    middleware = NetboxBranchGuardMiddleware(lambda r: SENTINEL)
    # conftest.py's PLUGINS_CONFIG sets api_bypass True globally; the API-aware
    # block-response tests need it False to actually reach the guard, matching
    # the real-world config under which the vprod regression was observed.
    middleware.api_bypass = api_bypass
    return middleware(request)


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    Interface.objects.all().delete()


def test_unresolvable_model_fails_open_on_main_ui():
    request = _prepare(factory.post("/config/", data={"tables": "x"}))
    assert _call(request) is SENTINEL


def test_unresolvable_model_fails_open_on_main_api():
    # api_bypass=False: exercise the model-resolution fail-open path itself,
    # not api_bypass's own unconditional "/api/ passes through" shortcut.
    request = _prepare(factory.post("/api/config/", data={"tables": "x"}))
    assert _call(request, api_bypass=False) is SENTINEL


def test_blocked_write_on_main_via_api_returns_json_403(stub_supports_branching):
    stub_supports_branching(True)
    iface = Interface.objects.create(name="eth0", status="active", description="d")

    request = _prepare(factory.post(
        f"/api/interfaces/{iface.pk}/edit/",
        data=json.dumps({"name": "renamed"}),  # 'name' isn't in excluded_fields - blocked
        content_type="application/json",
    ))
    response = _call(request, api_bypass=False)

    assert response is not SENTINEL
    assert response.status_code == 403
    assert response["Content-Type"].startswith("application/json")
    assert "restricted" in response.content.decode()


def test_blocked_write_on_main_via_ui_still_redirects(stub_supports_branching):
    stub_supports_branching(True)
    iface = Interface.objects.create(name="eth0", status="active", description="d")

    request = _prepare(factory.post(
        f"/interfaces/{iface.pk}/edit/",
        data={"name": "renamed"},
    ))
    response = _call(request)

    assert response is not SENTINEL
    assert response.status_code == 302
