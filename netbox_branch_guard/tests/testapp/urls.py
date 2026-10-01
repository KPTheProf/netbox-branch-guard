from django.urls import path

from . import views

urlpatterns = [
    path("devices/edit/", views.DeviceBulkEditView.as_view(), name="device_bulk_edit"),
    path("devices/<int:pk>/edit/", views.DeviceEditView.as_view(), name="device_edit"),
]
