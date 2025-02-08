from django.contrib import admin
from .models import Camera, Alert

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'ip_address', 'is_active', 'last_accessed')
    list_filter = ('is_active', 'location')
    search_fields = ('name', 'location', 'ip_address')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('timestamp_vid', 'camera', 'threat_type', 'confidence', 'is_reviewed')
    list_filter = ('threat_type', 'is_reviewed', 'camera')
    search_fields = ('camera__name', 'threat_type')
    date_hierarchy = 'timestamp'
