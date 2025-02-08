import cv2
import threading
from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse
from .setup import initialize_video_processor

class VideoCamera:
    def __init__(self):
        # List of camera backends to try
        self.backends = [
            cv2.CAP_ANY,          # Auto-detect
            cv2.CAP_V4L2,         # Video4Linux2
            cv2.CAP_DSHOW,        # DirectShow (Windows)
            cv2.CAP_MSMF,         # Microsoft Media Foundation
            cv2.CAP_GSTREAMER     # GStreamer
        ]

        self.video = None
        self.connect_to_camera()

        if self.video is None or not self.video.isOpened():
            raise ValueError("No working camera found!")

        # Initialize video properties
        self.grabbed, self.frame = self.video.read()
        self.lock = threading.Lock()
        self.processor = initialize_video_processor()

        # Start background frame grabbing
        self.stop_thread = False
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def connect_to_camera(self):
        # Try different camera indices
        for camera_idx in range(2):  # Try camera index 0 and 1
            for backend in self.backends:
                try:
                    print(f"Trying camera {camera_idx} with backend {backend}")
                    self.video = cv2.VideoCapture(camera_idx, backend)
                    if self.video is not None and self.video.isOpened():
                        # Test reading a frame
                        ret, frame = self.video.read()
                        if ret and frame is not None:
                            print(f"Successfully connected to camera {camera_idx} using backend {backend}")
                            return
                        else:
                            self.video.release()
                except Exception as e:
                    print(f"Failed to open camera {camera_idx} with backend {backend}: {e}")
                    if self.video is not None:
                        self.video.release()
                        self.video = None

    def __del__(self):
        self.stop_thread = True
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
        if self.video is not None:
            self.video.release()

    def get_frame(self):
        try:
            with self.lock:
                if self.frame is None:
                    print("No frame available")
                    return None

                # Make a copy to avoid threading issues
                frame = self.frame.copy()
                frame = cv2.flip(frame, 1)  # Horizontal flip

            try:
                # Process frame for action recognition
                result = self.processor.process_frame(frame)

                if result and isinstance(result, dict):
                    if result.get('class_name', '').lower() != 'normal':
                        # Draw detection information
                        confidence = result.get('confidence', 0)
                        class_name = result.get('class_name', 'Unknown')
                        frame_number = result.get('frame_number', 0)

                        # Format display text
                        label = f"{class_name}: {confidence:.2f}%"
                        frame_info = f"Frame: {frame_number}"



                        # Save alert if confidence is high enough
                        if confidence > 90:
                            # Draw main label
                            cv2.putText(
                                frame,
                                label,
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.9,
                                (0, 0, 255),  # Red color for alerts
                                2
                            )

                            # Draw frame counter
                            cv2.putText(
                                frame,
                                frame_info,
                                (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (255, 255, 255),  # White color for frame counter
                                1
                            )

                            # Adjust threshold as needed
                            try:
                                alert_data = self.processor.save_alert(
                                    frame,
                                    result,
                                    "alerts",
                                    camera_id=None
                                )
                                if alert_data:
                                    print(f"Alert saved: {alert_data}")
                            except Exception as e:
                                print(f"Error saving alert: {e}")
                                if hasattr(self, 'video'):
                                    self.video.release()
                                import sys
                                sys.exit(1)

                # Encode frame to JPEG
                ret, jpeg = cv2.imencode('.jpg', frame)
                if not ret:
                    raise Exception("Failed to encode frame")
                return jpeg.tobytes()

            except Exception as e:
                print(f"Error processing frame: {e}")
                # Try to encode and return the original frame before exiting
                ret, jpeg = cv2.imencode('.jpg', frame)
                if ret:
                    print("Returning last frame before exit")
                    if hasattr(self, 'video'):
                        self.video.release()
                    import sys
                    sys.exit(1)
                else:
                    print("Failed to encode last frame")
                    if hasattr(self, 'video'):
                        self.video.release()
                    import sys
                    sys.exit(1)

        except Exception as e:
            print(f"Critical error in get_frame: {e}")
            if hasattr(self, 'video'):
                self.video.release()
            import sys
            sys.exit(1)

    def update(self):
        while not self.stop_thread:
            if self.video is None or not self.video.isOpened():
                print("Camera disconnected, attempting to reconnect...")
                self.connect_to_camera()
                if self.video is None:
                    break
                continue

            grabbed, frame = self.video.read()
            with self.lock:
                if grabbed and frame is not None:
                    self.frame = frame
                else:
                    self.frame = None
                    print("Failed to grab frame, camera may be disconnected")
                    self.video.release()
                    self.video = None

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            break