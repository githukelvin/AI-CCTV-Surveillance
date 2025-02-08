import os
from datetime import datetime
import cv2
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from pathlib import Path
import uuid

from .setup import initialize_video_processor


class VideoFileHandler:
    def __init__(self):
        # Define upload and results directories
        self.upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'videos')
        self.results_dir = os.path.join(settings.MEDIA_ROOT, 'results')

        # Create directories if they don't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

    def save_uploaded_video(self, video_file):
        """Save uploaded video file with unique name"""
        # Generate unique filename
        ext = Path(video_file.name).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"

        # Save file
        fs = FileSystemStorage(location=self.upload_dir)
        filename = fs.save(unique_filename, video_file)

        return {
            'filename': filename,
            'filepath': os.path.join(self.upload_dir, filename),
            'url': fs.url(filename)
        }

    def create_result_directory(self, video_filename):
        """Create unique directory for analysis results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_dir = os.path.join(
            self.results_dir,
            f"{Path(video_filename).stem}_{timestamp}"
        )
        os.makedirs(result_dir, exist_ok=True)
        return result_dir

    def clean_old_files(self, max_age_days=7):
        """Clean up old uploaded videos and results"""
        current_time = datetime.now()

        # Clean uploads
        for file in os.listdir(self.upload_dir):
            file_path = os.path.join(self.upload_dir, file)
            if os.path.isfile(file_path):
                file_age = datetime.fromtimestamp(os.path.getctime(file_path))
                if (current_time - file_age).days > max_age_days:
                    os.remove(file_path)

        # Clean results
        for dir_name in os.listdir(self.results_dir):
            dir_path = os.path.join(self.results_dir, dir_name)
            if os.path.isdir(dir_path):
                dir_age = datetime.fromtimestamp(os.path.getctime(dir_path))
                if (current_time - dir_age).days > max_age_days:
                    for root, dirs, files in os.walk(dir_path, topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    os.rmdir(dir_path)


def get_top_probabilities(probabilities, class_labels, top_n=3):
    """Get top N probabilities with their class labels"""
    # Create list of (probability, label) tuples
    prob_pairs = list(zip(probabilities, class_labels))
    # Sort by probability in descending order and get top N
    top_probs = sorted(prob_pairs, key=lambda x: x[0], reverse=True)[:top_n]
    # Format as list of dicts
    return [
        {'label': label, 'probability': float(prob * 100)}
        for prob, label in top_probs
    ]

# def process_uploaded_video(video_path, processor=None, save_dir='/media/alerts'):
#     """Process uploaded video file and return results"""
#     if processor is None:
#         processor = initialize_video_processor()
#
#     results = []
#     alerts = []
#
#     try:
#         # Process video file
#         detections = processor.process_video_file(video_path)
#
#         for result in detections:
#             # Save alert
#             alert = processor.save_alert(
#                 result['frame'],
#                 result['prediction'],
#                 save_dir
#             )
#
#             if alert:  # Only append if alert was saved successfully
#                 alerts.append(alert)
#
#             # Add result to results list
#             results.append({
#                 'frame_number': result['prediction']['frame_number'],
#                 'prediction': {
#                     'class_name': result['prediction']['class_name'],
#                     'confidence': result['prediction']['confidence'],
#                     'predicted_class_idx': result['prediction']['predicted_class_idx'],
#                     'probabilities': result['prediction']['probabilities'].tolist(),
#                     'image_path': alert['image_path'] if alert else None
#                 }
#             })
#
#             # Print detection details (optional, can be removed in production)
#             print(f"Frame {result['prediction']['frame_number']}")
#             print(f"Class: {result['prediction']['class_name']}")
#             print(f"Confidence: {result['prediction']['confidence']:.2f}%")
#
#     except Exception as e:
#         print(f"Error processing video: {str(e)}")
#         return []
#
#     return results
# def process_uploaded_video(video_path, processor=None, save_dir='surveillance_project/surveillance_project/media/alerts'):
#     if processor is None:
#         processor = initialize_video_processor()
#
#     results = []
#     try:
#         detections = processor.process_video_file(video_path)
#
#         for result in detections:
#             # Get top 3 probabilities
#             top_probs = get_top_probabilities(
#                 result['prediction']['probabilities'],
#                 processor.class_labels
#             )
#             if result['prediction']['confidence'] > 65:
#                 alert = processor.save_alert(
#                     result['frame'],
#                     result['prediction'],
#                     save_dir
#                 )
#                 if alert:  # Check if alert was saved successfully
#                     print(f"Alert saved: {alert['type']} at frame {alert['frame_number']}")
#
#
#
#             results.append({
#                 'frame_number': result['prediction']['frame_number'],
#                 'prediction': {
#                     'class_name': result['prediction']['class_name'],
#                     'confidence': result['prediction']['confidence'],
#                     'predicted_class_idx': result['prediction']['predicted_class_idx'],
#                     'top_probabilities': top_probs
#                 }
#             })
#     except Exception as e:
#         print(f"Error processing video: {str(e)}")
#         return []
#
#     return results

from datetime import datetime, time


def frame_to_time(frame_num, fps):
    """Convert frame number to time object"""
    total_seconds = frame_num / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    microseconds = int((total_seconds * 1000000) % 1000000)

    # Create time object
    frame_time = time(
        hour=hours,
        minute=minutes,
        second=seconds,
        microsecond=microseconds
    )

    return {
        'time_obj': frame_time,
        'formatted': frame_time.strftime('%H:%M:%S.%f')[:-3],  # Show only milliseconds
        'total_seconds': total_seconds
    }


def process_uploaded_video(video_path, processor=None, camera_id=None):
    if processor is None:
        processor = initialize_video_processor()

    results = []
    all_detections = []

    try:
        # Open video to get properties
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        print(f"Video FPS: {fps}")
        video.release()

        detections = processor.process_video_file(video_path)

        # Process all frames and store them with confidence scores
        for result in detections:
            frame_num = result['prediction']['frame_number']
            time_data = frame_to_time(frame_num, fps)

            # Get top probabilities
            top_probs = get_top_probabilities(
                result['prediction']['probabilities'],
                processor.class_labels
            )

            # Add time and top probabilities to prediction
            result['prediction'].update({
                'timestamp': time_data['formatted'],
                'timestamp_vid': time_data['time_obj'],  # Store as time object
                'frame_time': time_data['total_seconds'],
                'fps': fps,
                'top_probabilities': top_probs
            })

            # Store detection with its confidence
            all_detections.append({
                'confidence': result['prediction']['confidence'],
                'result': result
            })

        # Sort and process top 5 detections
        top_detections = sorted(
            all_detections,
            key=lambda x: x['confidence'],
            reverse=True
        )[:5]

        print(f"Found {len(all_detections)} total detections. Processing top 5 by confidence.")

        # Process only the top 5 confidence detections
        for detection in top_detections:
            result = detection['result']

            print(f"Processing detection with timestamp: {result['prediction']['timestamp']}")

            # Save alert for each top detection
            alert = processor.save_alert(
                result['frame'],
                result['prediction'],
                None,
                camera_id
            )

            if alert:
                # For response JSON, format the time as string
                formatted_time = result['prediction']['timestamp_vid'].strftime('%H:%M:%S.%f')[:-3]

                results.append({
                    'frame_number': result['prediction']['frame_number'],
                    'timestamp': formatted_time,
                    'prediction': {
                        'class_name': result['prediction']['class_name'],
                        'confidence': result['prediction']['confidence'],
                        'predicted_class_idx': result['prediction']['predicted_class_idx'],
                        'top_probabilities': result['prediction']['top_probabilities'],
                        'alert_id': alert['id'],
                        'timestamp_vid': formatted_time,
                        'fps': fps,
                        'frame_time': result['prediction']['frame_time'],
                        'image_url': alert['image_url']
                    }
                })

        print(f"\nSaved {len(results)} alerts with highest confidence scores:")
        for idx, res in enumerate(results, 1):
            print(f"{idx}. Time {res['timestamp']} (Frame {res['frame_number']}): "
                  f"{res['prediction']['class_name']} - "
                  f"Confidence: {res['prediction']['confidence']:.2f}%")

    except Exception as e:
        print(f"Error processing video: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

    return results
"""
if __name__ == "__main__":
    # Example configuration
    video_path = '/home/de-coder/Videoclassification/surveillance_project/media/uploads/videos/ca2f40d5-b7ce-4f06-bdd1-5a2411f90001.mp4'
    save_dir = 'surveillance_project/media/alerts'

    # Initialize processor
    processor = initialize_video_processor()

    # Process a video file
    results = process_uploaded_video(video_path, processor, save_dir)

    # Print results
    for result in results:
        print(f"Frame {result['frame_number']}")
        print(f"Class: {result['prediction']['class_name']}")
        print(f"Confidence: {result['prediction']['confidence']:.2f}%")
        if result['prediction']['image_path']:
            print(f"Image saved: {result['prediction']['image_path']}")
"""