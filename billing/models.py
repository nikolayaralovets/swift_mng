from django.db import models
from django.utils import timezone

# Create your models here.

class Audit(models.Model):
    datetime = models.DateTimeField(default=timezone.now)
    user = models.CharField(max_length=32)
    type = models.CharField(max_length=16)
    objtype = models.CharField(max_length=16)
    object = models.CharField(max_length=32)
    details = models.TextField()
