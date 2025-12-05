import os
import logging
import torch
import sys

# Add base directory to path if needed, though usually handled in app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(BASE_DIR) 

class Config:
    # --- Security & Core Configuration ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "your_strong_fallback_key")

    # CRITICAL FIX: Use environment variables for secure database connection
    DB_USER = os.environ.get("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "reshu890")
    DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
    DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
    DB_NAME = os.environ.get("POSTGRES_DB", "merged_db")

    SQLALCHEMY_DATABASE_URI = (
        f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- Application Defaults (Required for UUID handling) ---
    DEFAULT_USER_ID = os.environ.get(
        "DEFAULT_USER_ID", 
        "00000000-0000-7000-0000-000000000001"
    )

    # --- Storage Configuration ---
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    STORAGE_FOLDER = os.path.join(BASE_DIR, 'storage')
    ANNOTATED_FOLDER = os.path.join(STORAGE_FOLDER, 'annotated')

    # FIX: Add the missing configuration variable required by the controller
    DETECTION_IMAGE_FOLDER = STORAGE_FOLDER

    POTHOLE_ORIGINAL_FOLDER = os.path.join(STORAGE_FOLDER, 'pothole', 'original')
    POTHOLE_DETECTED_FOLDER = os.path.join(STORAGE_FOLDER, 'pothole', 'detected')

    WASTE_ORIGINAL_FOLDER = os.path.join(STORAGE_FOLDER, 'waste', 'original')
    WASTE_DETECTED_FOLDER = os.path.join(STORAGE_FOLDER, 'waste', 'detected')
    
    # Create folders immediately upon class definition
    os.makedirs(STORAGE_FOLDER, exist_ok=True) 
    os.makedirs(POTHOLE_ORIGINAL_FOLDER, exist_ok=True)
    os.makedirs(POTHOLE_DETECTED_FOLDER, exist_ok=True)
    os.makedirs(WASTE_ORIGINAL_FOLDER, exist_ok=True)
    os.makedirs(WASTE_DETECTED_FOLDER, exist_ok=True)
    os.makedirs(ANNOTATED_FOLDER, exist_ok=True)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


# --- ModelLoader Class ---
try:
    from ultralytics import YOLO
except ImportError:
    # Define a mock YOLO class if ultralytics is not available for testing purposes
    class YOLO:
        def __init__(self, path):
            pass
        def __call__(self, *args, **kwargs):
            return []
        @property
        def names(self):
            return {0: "mock_class"}


class ModelLoader:
    def __init__(self, waste_model_path, pothole_model_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Loading YOLO models on {self.device.upper()}...")

        if not os.path.exists(waste_model_path):
            raise FileNotFoundError(f"Waste model not found: {waste_model_path}")

        if not os.path.exists(pothole_model_path):
            raise FileNotFoundError(f"Pothole model not found: {pothole_model_path}")

        try:
            self.waste_model = YOLO(waste_model_path)
            self.pothole_model = YOLO(pothole_model_path)
            logging.info("Models loaded successfully.")
        except Exception as e:
            logging.exception("Failed to load YOLO models.")
            raise e

    def predict(self, image_path, task_type="waste", conf=0.25, imgsz=640):
        model = self.waste_model if task_type == "waste" else self.pothole_model

        return model(
            source=image_path,
            conf=conf,
            imgsz=imgsz,  # Fixed typo here
            device=self.device 
        )

    def get_class_name(self, task_type, class_id):
        """Return class name from YOLO model."""
        if task_type == "waste":
            return self.waste_model.names.get(class_id, "unknown")
        elif task_type == "pothole":
            return self.pothole_model.names.get(class_id, "unknown")
        return "unknown"
