from .config import VideoProcessorConfig
from .video_processor import VideoProcessor

def initialize_video_processor():
    """Initialize VideoProcessor with configuration"""
    processor = VideoProcessor(model_path=VideoProcessorConfig.MODEL_PATH)
    return processor

def process_camera_feed(camera_url, processor=None):
    """Process camera feed and generate alerts"""
    if processor is None:
        processor = initialize_video_processor()

    for detection in processor.process_video_stream(
            camera_url,
            confidence_threshold=VideoProcessorConfig.CONFIDENCE_THRESHOLD
    ):
        alert = processor.save_alert(
            detection['frame'],
            detection['prediction'],
            VideoProcessorConfig.ALERT_SAVE_DIR
        )
        yield alert
