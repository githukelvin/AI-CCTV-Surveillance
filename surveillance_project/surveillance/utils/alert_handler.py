from django.core.files.base import ContentFile
from django.utils import timezone
import cv2
import os
import numpy as np
from pathlib import Path
from ..models import Alert, Camera


class AlertHandler:
    def __init__(self):
        self.class_to_threat_map = {
            'Robbery': 'Robbery',
            'Vandalism': 'Vandalism',
            'Shoplifting': 'Shoplifting',
            'Burglary': 'Burglary',
            'Stealing': 'Stealing',
        }

    def map_class_to_threat(self, class_name):
        """Map model class to alert threat type"""
        return self.class_to_threat_map.get(class_name, 'suspicious')

    def save_frame_as_image(self, frame):
        """Convert frame to image file"""
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            return None
        return ContentFile(buffer.tobytes())

    def create_alert(self, frame, prediction, camera_id=None):
        """Create Alert instance from detection"""
        try:
            # Get camera instance
            camera = None

            # Map the class to threat type
            threat_type = self.map_class_to_threat(prediction['class_name'])

            # Convert frame to image file
            image_file = self.save_frame_as_image(frame)
            if image_file is None:
                raise ValueError("Failed to convert frame to image")

            # Create the alert instance
            alert = Alert(
                camera=camera,
                threat_type=threat_type,
                confidence=prediction['confidence'],
                timestamp_vid=prediction['timestamp_vid'],
                timestamp=timezone.now()
            )

            # Save image file
            image_filename = f"alert_{alert.timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            alert.image.save(image_filename, image_file, save=False)

            # For now, video_clip is optional since we're working with frames
            # You can add video clip saving later if needed

            # Save the alert
            alert.save()

            return {
                'id': alert.id,
                'threat_type': alert.threat_type,
                'confidence': alert.confidence,
                'timestamp': alert.timestamp,
                'image_url': alert.image.url if alert.image else None,
                'class_name': prediction['class_name'],
                'frame_number': prediction.get('frame_number', 0),
                'top_probabilities': prediction.get('top_probabilities', [])
            }

        except Exception as e:
            print(f"Error creating alert: {str(e)}")
            return None