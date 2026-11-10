from django.http import HttpResponse
from django.views import View

from .models import Interface


class InterfaceEditView(View):
    queryset = Interface.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")


class ConfigLikeView(View):
    """
    Deliberately exposes no queryset/model attribute, matching NetBox's own
    UserConfigViewSet (users.api.views) - a config endpoint with a get_queryset()
    *method*, bound per-request, rather than a class attribute _resolve_model()
    can introspect.
    """

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")

    def patch(self, request, *args, **kwargs):
        return HttpResponse("ok")
