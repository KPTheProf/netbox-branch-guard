from django.urls import path

from . import views

urlpatterns = [
    path("devices/<int:pk>/edit/", views.DeviceEditView.as_view(), name="device_edit"),
    path("devices/<int:pk>/delete/", views.DeviceDeleteView.as_view(), name="device_delete"),
    path("devices/delete/", views.DeviceBulkDeleteView.as_view(), name="device_bulk_delete"),
]
