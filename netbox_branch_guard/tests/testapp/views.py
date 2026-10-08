from django.http import HttpResponse
from django.views import View

from .models import Interface


class InterfaceEditView(View):
    queryset = Interface.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")
