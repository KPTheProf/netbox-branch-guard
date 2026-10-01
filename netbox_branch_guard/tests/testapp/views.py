from django.http import HttpResponse
from django.views import View

from .models import Device


class DeviceBulkEditView(View):
    queryset = Device.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")


class DeviceEditView(View):
    queryset = Device.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")
