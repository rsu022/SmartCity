import os
from flask import Blueprint, request, jsonify, current_app 
import logging
from datetime import datetime

from services.inference_service import InferenceService 
from model_loader import ModelLoader 
from utils.file_utils import save_upload 

from controller.detection_controller import (
    create_detection,
    get_my_single,
    get_my_detections,
    get_my_by_type,
    update_my_detection,
    delete_my_detection,
    delete_all_my_by_type,
    get_detections_by_user,
    get_user_full_details
)

from models.db import db
from models.detection import Detection
from models.user_model import User

logger = logging.getLogger(__name__)

detect_ml_bp = Blueprint("detect_ml", __name__)

model_loader = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)
inference = InferenceService(model_loader)


@detect_ml_bp.route("/detects", methods=["POST"])
def detect_route():
    try:         
        json_data = request.get_json(silent=True) or {}
        
        user_id = request.form.get("user_id") if request.form else json_data.get("user_id")
        task_type = request.form.get("task_type") if request.form else json_data.get("task_type", "waste")
        task_type = task_type or "waste"

               
        if "image" in request.files:
            file = request.files["image"]
            saved_path = save_upload(file)  

            result = inference.run(
                image_path=saved_path,
                user_id=user_id,
                task_type=task_type
            )                        
            if user_id:
                try:
                    user = User.query.filter_by(id=user_id).first() 
                    if user:
                        new_detection = Detection(
                            user_id=user.id,
                            detection_type=task_type,
                            image_name=os.path.basename(saved_path),
                            latitude=json_data.get("latitude"),
                            longitude=json_data.get("longitude"),
                            location=json_data.get("location"),
                            created_at=datetime.utcnow()
                        )
                        db.session.add(new_detection)
                        db.session.commit()
                except Exception as e:
                    logger.warning(f"Failed to save detection to DB: {e}")

            return jsonify(result), 200
                    
        image_name = json_data.get("image_name")

        if image_name:          
            if task_type == "waste":
                folder = "storage\waste\detected"
            elif task_type == "pothole":
                folder = "storage\pothole\detected"
            else:
                return jsonify({"success": False, "error": "Invalid task_type"}), 400

            img_path = os.path.join(folder, image_name)

            if not os.path.exists(img_path):
                return jsonify({
                    "success": False,
                    "error": "Image not found",
                    "path": img_path
                }), 404

            result = inference.run(
                image_path=img_path,
                user_id=user_id,
                task_type=task_type
            )

            return jsonify(result), 200
                    
        return jsonify({
            "success": False,
            "error": "No file or image_name provided"
        }), 400

    except Exception as e:
        logger.exception("Detection API error")
        return jsonify({"success": False, "error": str(e)}), 500

detection_bp = Blueprint("detection_bp", __name__, url_prefix="/detections")

detection_bp.route("/", methods=["POST"])(create_detection)
detection_bp.route("/my", methods=["GET"])(get_my_detections)
detection_bp.route("/type/<string:detection_type>", methods=["GET"])(get_my_by_type)
detection_bp.route("/my/<string:id>", methods=["GET"])(get_my_single)
detection_bp.route("/user/<string:user_id>", methods=["GET"])(get_detections_by_user)
detection_bp.route("/user/details/<string:user_id>", methods=["GET"])(get_user_full_details)
detection_bp.route("/my/update/<string:id>", methods=["PUT"])(update_my_detection)
detection_bp.route("/my/<string:id>", methods=["DELETE"])(delete_my_detection)
detection_bp.route("/my/delete<string:detection_type>", methods=["DELETE"])(delete_all_my_by_type)