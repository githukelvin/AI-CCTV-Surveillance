from django.db import models

class Camera(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=8080)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    last_accessed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.location})"

    class Meta:
        ordering = ['name']
