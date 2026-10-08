from django.http import HttpResponse
from django.views import View

from .models import Device


class DeviceEditView(View):
    queryset = Device.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")


class DeviceDeleteView(View):
    queryset = Device.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")


class DeviceBulkDeleteView(View):
    queryset = Device.objects.all()

    def post(self, request, *args, **kwargs):
        return HttpResponse("ok")
