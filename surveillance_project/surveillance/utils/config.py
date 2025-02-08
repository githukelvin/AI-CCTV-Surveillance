# config.py
class VideoProcessorConfig:

    MODEL_PATH = '/home/de-coder/Videoclassification/surveillance_project/AI_Model/c3d_best_v1.h5'  # Update with your model path
    ALERT_SAVE_DIR = 'surveillance_project/media/alerts'  # Update with your save directory
    CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence to generate alert