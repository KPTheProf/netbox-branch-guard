from django.urls import path

from . import views

urlpatterns = [
    path("interfaces/<int:pk>/edit/", views.InterfaceEditView.as_view(), name="interface_edit"),
    path("api/interfaces/<int:pk>/edit/", views.InterfaceEditView.as_view(), name="api_interface_edit"),
    path("config/", views.ConfigLikeView.as_view(), name="config_like"),
    path("api/config/", views.ConfigLikeView.as_view(), name="api_config_like"),
]
