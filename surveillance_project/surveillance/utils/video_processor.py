import cv2
import torch
import numpy as np
from PIL import Image

from torchvision import transforms
from django.utils import timezone  # Add this import
import os
import sys

from .alert_handler import AlertHandler
from .mailings import ThreatStatistics

# Get the absolute path to the project root (Videoclassification directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from model import resnet50

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User


# def _format_email_content(alert_data, threat_stats, camera_id): #Remove self
#     """Format email content with threat statistics"""
#     print("Entering _format_email_content") # Debug print
#
#     print(f"alert_data: {alert_data}") # Debug print
#     print(f"threat_stats: {threat_stats}") # Debug print
#     # print(f"camera_id: {camera_id}") # Debug print
#
#     content = f"""
#     🚨 Security Alert Notification 🚨
#
#     New Alert Details:
#     -----------------
#     Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#     Threat Type: {alert_data.get('threat_type', 'Unknown')}
#     Confidence: {alert_data.get('confidence', 0):.2f}%
#
#     Threat Statistics ({threat_stats['time_window']}):
#     ------------------------
#     Total Alerts: {threat_stats['total_alerts']}
#
#     Threat Type Distribution:
#     """
#
#     # Add threat counts
#     for threat in threat_stats['threat_counts']:
#         content += f"\n- {threat['threat_type']}: {threat['count']} alerts"
#
#     content += "\n\nTop 3 Highest Probability Threats:"
#     for idx, threat in enumerate(threat_stats['top_threats'], 1):
#         content += f"\n{idx}. {threat['threat_type']} - {threat['confidence']:.2f}%" # Corrected .confidence
#
#     content += "\n\nPlease review these alerts in the security dashboard for more details."
#
#     print(f"Formatted email content: {content}") # Debug print
#
#     return content

class VideoProcessor:
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.sequence_length = 16
        self.im_size = 128
        self.class_labels = ['Robbery', 'Vandalism', 'Shoplifting', 'normal', 'Burglary', 'Stealing']

        self.transform = transforms.Compose([
            transforms.Resize((self.im_size, self.im_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.4889, 0.4887, 0.4891],
                std=[0.2074, 0.2074, 0.2074]
            )
        ])

        if model_path and os.path.exists(model_path):
            self.model = resnet50(class_num=len(self.class_labels)).to(self.device)
            self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
            self.model.eval()
        else:
            self.model = None

        self.frame_buffer = []
        self.processed_frames = 0

    def preprocess_frames(self, frames):
        if len(frames) < self.sequence_length:
            last_frame = frames[-1]
            frames.extend([last_frame] * (self.sequence_length - len(frames)))

        if len(frames) > self.sequence_length:
            indices = np.linspace(0, len(frames) - 1, self.sequence_length, dtype=int)
            frames = [frames[i] for i in indices]

        transformed_frames = [self.transform(frame) for frame in frames]
        frames_tensor = torch.stack(transformed_frames, dim=1)
        return frames_tensor.unsqueeze(0)

    def process_video_file(self, video_path):
        """Process entire video file at once and return all results"""
        if self.model is None:
            return None

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")

        frames = []
        original_frames = []  # Store original frames for output
        results = []
        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                # Store original frame
                original_frames.append(frame.copy())

                # Process frame for model
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))

                if len(frames) >= self.sequence_length:
                    # Process the sequence
                    input_tensor = self.preprocess_frames(frames)
                    input_tensor = input_tensor.to(self.device)

                    with torch.no_grad():
                        predictions = self.model(input_tensor)
                        probabilities = torch.nn.functional.softmax(predictions, dim=1)
                        pred_class = torch.argmax(probabilities, dim=1).item()
                        confidence = probabilities[0][pred_class].item()

                    # Use the last frame from original_frames for the result
                    result = {
                        'frame': original_frames[-1],  # Use the last original frame
                        'prediction': {
                            'predicted_class_idx': pred_class,
                            'confidence': confidence * 100,
                            'class_name': self.class_labels[pred_class],
                            'probabilities': probabilities[0].cpu().numpy(),
                            'frame_number': frame_count
                        }
                    }
                    results.append(result)

                    # Clear processed frames but keep the last one for overlap
                    frames = frames[-1:]
                    original_frames = original_frames[-1:]

            # Process any remaining frames
            if len(frames) > 0:
                input_tensor = self.preprocess_frames(frames)
                input_tensor = input_tensor.to(self.device)

                with torch.no_grad():
                    predictions = self.model(input_tensor)
                    probabilities = torch.nn.functional.softmax(predictions, dim=1)
                    pred_class = torch.argmax(probabilities, dim=1).item()
                    confidence = probabilities[0][pred_class].item()

                result = {
                    'frame': original_frames[-1],  # Use the last original frame
                    'prediction': {
                        'predicted_class_idx': pred_class,
                        'confidence': confidence * 100,
                        'class_name': self.class_labels[pred_class],
                        'probabilities': probabilities[0].cpu().numpy(),
                        'frame_number': frame_count
                    }
                }
                results.append(result)

        finally:
            cap.release()

        return results
    def process_video_stream(self, camera_url, confidence_threshold=0.7):
        """Process live video stream from camera"""
        cap = cv2.VideoCapture(camera_url)
        if not cap.isOpened():
            raise ValueError(f"Failed to open camera stream: {camera_url}")

        self.frame_buffer = []
        self.processed_frames = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                result = self.process_frame(frame)

                if result is not None and result['confidence'] > confidence_threshold * 100:
                    if result['class_name'].lower() != 'normal':
                        yield {
                            'frame': frame,
                            'prediction': result
                        }

        finally:
            cap.release()

    def process_frame(self, frame):
        """Process a single frame for live streaming"""
        if self.model is None:
            return None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)

        self.frame_buffer.append(image)
        self.processed_frames += 1

        if len(self.frame_buffer) >= self.sequence_length:
            input_tensor = self.preprocess_frames(self.frame_buffer)
            input_tensor = input_tensor.to(self.device)

            with torch.no_grad():
                predictions = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(predictions, dim=1)
                pred_class = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][pred_class].item()

                self.frame_buffer = []

                return {
                    'predicted_class_idx': pred_class,
                    'confidence': confidence * 100,
                    'class_name': self.class_labels[pred_class],
                    'probabilities': probabilities[0].cpu().numpy(),
                    'frame_number': self.processed_frames
                }

        return None

    def save_alert(self, frame, alert_info,timestamp_vid, save_dir, camera_id=None):
        """Save alert information and send email notification"""
        if frame is None or not isinstance(frame, np.ndarray):
            print(f"Warning: Invalid frame data received: {type(frame)}")
            return None

        if frame.size == 0:
            print("Warning: Empty frame received")
            return None

        try:
            # Create alert handler
            alert_handler = AlertHandler()

            # Create alert and get response
            alert_data = alert_handler.create_alert(
                frame=frame,
                prediction=alert_info,
                camera_id=camera_id,
            )

            if alert_data:
                # Get threat statistics
                stats = ThreatStatistics()
                threat_stats = stats.get_threat_statistics_test(time_window_minutes=15)

                # Format email content
                email_content = self._format_email_content(
                    alert_data=alert_data,
                    threat_stats=threat_stats,
                    camera_id=camera_id
                )

                # Send email to all active staff users
                self._send_notification_email(email_content)

            return alert_data

        except Exception as e:
            print(f"Error in save_alert: {str(e)}")
            return None

    def _format_email_content(self, alert_data, threat_stats, camera_id):
        """Format email content with threat statistics"""
        try:
            # Print debug information
            print("=== Email Content Debug ===")
            print(f"Alert data type: {type(alert_data)}")
            print(f"Alert data content: {alert_data}")
            print(f"Threat stats: {threat_stats}")

            content = [
                "🚨 Security Alert Notification 🚨\n",
                "New Alert Details:",
                "-----------------",
                f"Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Camera ID: {camera_id}",
                f"Threat Type: {alert_data.get('threat_type', 'Unknown')}",  # Changed to dictionary access
                f"Confidence: {alert_data.get('confidence', 0):.2f}%\n",  # Changed to dictionary access
                f"Threat Statistics ({threat_stats.get('time_window', '15 minutes')})",
                "------------------------",
                f"Total Alerts: {threat_stats.get('total_alerts', 0)}\n",
                "Threat Type Distribution:"
            ]

            # Add threat counts with safety checks
            for threat in threat_stats.get('threat_counts', []):
                if isinstance(threat, dict):
                    content.append(f"- {threat.get('threat_type', 'Unknown')}: {threat.get('count', 0)} alerts")

            content.append("\nTop 3 Highest Probability Threats:")

            # Add top threats with safety checks
            for idx, threat in enumerate(threat_stats.get('top_threats', []), 1):
                try:
                    # Handle both model instances and dictionaries
                    if hasattr(threat, 'threat_type') and hasattr(threat, 'confidence'):
                        # It's a model instance
                        content.append(f"{idx}. {threat.threat_type} - {threat.confidence:.2f}%")
                    else:
                        # It's a dictionary
                        content.append(
                            f"{idx}. {threat.get('threat_type', 'Unknown')} - {threat.get('confidence', 0):.2f}%"
                        )
                except Exception as e:
                    print(f"Error formatting top threat {idx}: {str(e)}")
                    continue

            content.append("\nPlease review these alerts in the security dashboard for more details.")

            # Join all lines with newlines
            return "\n".join(content)

        except Exception as e:
            print(f"Error formatting email content: {str(e)}")
            # Return a basic fallback message
            try:
                threat_type = alert_data.get('threat_type', 'Unknown Threat')
                return f"Security Alert: {threat_type} detected at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            except:
                return f"Security Alert detected at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    def _send_notification_email(self, content):
        """Send email notification to all active staff users"""
        print("=== Email Notification Debug ===")
        print(f"Current time: {timezone.now()}")
        print("Entering _send_notification_email")

        try:
            # Verify email settings
            print(f"Checking email settings:")
            print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
            print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
            print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

            # Get all active staff users' emails
            staff_emails = User.objects.filter(
                is_staff=True,
                is_active=True
            ).values_list('email', flat=True)

            staff_emails = list(staff_emails)  # Convert to list
            print(f"Staff emails found: {staff_emails}")

            if not staff_emails:
                print("No staff emails found for notification")
                return False

            # Validate email content
            if not isinstance(content, str):
                print(f"Invalid content type: {type(content)}")
                content = str(content)

            print("About to send email with following details:")
            print(f"Recipients: {staff_emails}")
            print(f"Content length: {len(content)} characters")

            # Send email
            email_status = send_mail(
                subject='Security Alert Notification',
                message=content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=staff_emails,
                fail_silently=False
            )

            if email_status:
                print("Email sent successfully")
                return True
            else:
                print("Email sending failed (returned 0)")
                return False

        except AttributeError as e:
            print(f"Settings configuration error: {str(e)}")
            print("Please check your Django email settings")
            return False
        except User.DoesNotExist:
            print("User model not accessible")
            return False
        except Exception as e:
            print(f"Error sending email notification: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Email content: {content}")
            return False