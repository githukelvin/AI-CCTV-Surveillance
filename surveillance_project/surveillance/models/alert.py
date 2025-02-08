from django.db import models
from .camera import Camera

class Alert(models.Model):
    THREAT_TYPES = [
        ('intrusion', 'Intrusion'),
        ('violence', 'Violence'),
        ('theft', 'Theft'),
        ('Shoplifting', 'Shoplifting'),
        ('Burglary', 'Burglary'),
        ('Stealing', 'Stealing'),
        ('normal', 'normal'),
        ('Vandalism', 'Vandalism'),
        ('Robbery', 'Robbery'),
        ('suspicious', 'Suspicious Activity'),
    ]

    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    threat_type = models.CharField(max_length=50, choices=THREAT_TYPES)
    confidence = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    timestamp_vid = models.TimeField(  # Add new time field for video timestamp
        # null=True,
        # blank=True,
        help_text="Video frame timestamp (HH:MM:SS.mmm)"
    )
    image = models.ImageField(upload_to='alerts/images/')
    video_clip = models.FileField(upload_to='alerts/videos/')
    is_reviewed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.threat_type} - {self.camera.name} ({self.timestamp})"

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.threat_type} - {self.timestamp}"

    def __str__(self):
        if self.timestamp_vid:
            return f"{self.threat_type} - {self.timestamp_vid.strftime('%H:%M:%S.%f')[:-3]}"
        return f"{self.threat_type} - {self.timestamp}"
