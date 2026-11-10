from django.db import models


class Interface(models.Model):
    name = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="active")
    description = models.CharField(max_length=200, blank=True, default="")
    enabled = models.BooleanField(default=True)

    class Meta:
        app_label = "testapp"
