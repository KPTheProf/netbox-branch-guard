"""
Minimal standalone Django setup so netbox_branch_guard can be unit-tested
without a real NetBox install (NetBox itself isn't pip-installable and
needs Postgres/Redis). We only stub the two symbols the plugin's package
__init__ needs at import time; the middleware under test is unmodified.
"""
import sys
import types

import django
from django.conf import settings


def _stub_netbox_plugins():
    if "netbox.plugins" in sys.modules:
        return
    netbox_pkg = types.ModuleType("netbox")
    plugins_mod = types.ModuleType("netbox.plugins")

    class PluginConfig:
        pass

    plugins_mod.PluginConfig = PluginConfig
    netbox_pkg.plugins = plugins_mod
    sys.modules["netbox"] = netbox_pkg
    sys.modules["netbox.plugins"] = plugins_mod


_stub_netbox_plugins()

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.messages",
            "netbox_branch_guard.tests.testapp",
        ],
        ROOT_URLCONF="netbox_branch_guard.tests.testapp.urls",
        MESSAGE_STORAGE="django.contrib.messages.storage.fallback.FallbackStorage",
        USE_TZ=True,
        PLUGINS_CONFIG={
            "netbox_branch_guard": {
                "enabled": True,
                "api_bypass": True,
                "superuser_bypass": False,
                "enforce_ownership": False,
                "logging": False,
                "excluded_models": [],
                "excluded_fields": ["status", "description"],
            }
        },
    )
    django.setup()

    from django.db import connection

    from netbox_branch_guard.tests.testapp.models import Interface

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Interface)
