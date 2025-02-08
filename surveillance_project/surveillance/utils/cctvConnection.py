# video_app/views.py
import cv2
import threading
from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt  # For handling POST requests

class VideoCameraCCTV(object):
    def __init__(self, rtsp_url):
        self.video = cv2.VideoCapture(rtsp_url)

        if not self.video.isOpened():
            raise Exception(f"Error opening video stream: {rtsp_url}")

        (self.grabbed, self.frame) = self.video.read()
        self.lock = threading.Lock()
        threading.Thread(target=self.update, args=()).start()

    def __del__(self):
        self.video.release()

    def get_frame(self):
        with self.lock:
            frame = self.frame.copy()
        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def update(self):
        while True:
            (self.grabbed, self.frame) = self.video.read()
            if self.grabbed:
                continue
            else:
                break
        self.video.release()

def genCCTV(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ... other view functions if needed