from django.db import models


class Device(models.Model):
    name = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="active")
    description = models.CharField(max_length=200, blank=True, default="")
    platform = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        app_label = "testapp"
