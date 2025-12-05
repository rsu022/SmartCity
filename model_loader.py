import os
import logging
import torch 
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class ModelLoader:
    def __init__(self, waste_model_path, pothole_model_path):
        # FIX: Dynamically determine the best device (CUDA if available, otherwise CPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading YOLO models on {self.device.upper()}...")

        if not os.path.exists(waste_model_path):
            raise FileNotFoundError(f"Waste model not found: {waste_model_path}")

        if not os.path.exists(pothole_model_path):
            raise FileNotFoundError(f"Pothole model not found: {pothole_model_path}")

        try:
            self.waste_model = YOLO(waste_model_path)
            self.pothole_model = YOLO(pothole_model_path)
            logger.info("Models loaded successfully.")
        except Exception as e:
            logger.exception("Failed to load YOLO models.")
            raise e

    def predict(self, image_path, task_type="waste", conf=0.25, imgsz=640):
        model = self.waste_model if task_type == "waste" else self.pothole_model

        # Pass the dynamically set device to the prediction call
        return model(
            source=image_path,
            conf=conf,
            imgsz=imgsz,
            device=self.device 
        )

    def get_class_name(self, task_type, class_id):
        """Return class name from YOLO model."""
        if task_type == "waste":
            return self.waste_model.names.get(class_id, "unknown")

        elif task_type == "pothole":
            return self.pothole_model.names.get(class_id, "unknown")

        return "unknown"