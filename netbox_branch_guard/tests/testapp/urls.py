from django.urls import path

from . import views

urlpatterns = [
    path("interfaces/<int:pk>/edit/", views.InterfaceEditView.as_view(), name="interface_edit"),
]
