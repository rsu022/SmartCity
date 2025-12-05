import os
import shutil
import time
from datetime import datetime
from flask import current_app
# Assuming these imports are available and necessary
from models import db, Detection, Image, Tag, DetectionTag, Department, DetectionDepartment
from services.model_loader__old import ModelLoader 
from utils.viz import annotate_and_save_ultralytics
from reasoning.kg_gnn import KnowledgeGraphReasoner
from processors.waste_processor import WasteProcessor
from processors.pothole_processor import PotholeProcessor


def _to_relative_storage(path: str):
    """Convert absolute path under STORAGE_FOLDER to '/storage/pothole/original/file.jpg'."""
    if not path:
        return None
    root = current_app.config.get("STORAGE_FOLDER")
    if not root:
        return path
    rel = os.path.relpath(path, root)
    return f"/storage/{rel.replace(os.sep, '/')}"

# Singletons
kg = KnowledgeGraphReasoner()
WASTE_PROCESSOR = WasteProcessor()
POTHOLE_PROCESSOR = PotholeProcessor()
MODEL_LOADER = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)

POTHOLE_MODEL = MODEL_LOADER.pothole_model
WASTE_MODEL = MODEL_LOADER.waste_model 

# --- FIX: Removed integer conversion logic ---
def _normalize_user_id(uid):
    """
    Ensures the user ID is treated as a string UUID.
    """
    if isinstance(uid, str) and len(uid) > 0:
        return uid
    return None

def save_to_database(detection_type, result):
    print("Using DB URI:", current_app.config['SQLALCHEMY_DATABASE_URI'])
    print("Saving detection payload:", result)  # <<< DEBUG PRINT

    # FIX: Get UUID string directly and use a fallback UUID if user_id is missing
    normalized_user_id = result.get("user_id")
    if normalized_user_id is None:
        # NOTE: Using a default placeholder UUID for unauthenticated requests if required
        normalized_user_id = current_app.config.get("DEFAULT_USER_ID", "00000000-0000-7000-0000-000000000001") 
        
    detection_payload = {
        "user_id": normalized_user_id, # Must be the UUID string
        "detection_type": detection_type,
        "image_name": result.get("image_name") or "",
        "image_path": result.get("image_path"), # ADDED: image_path
        "detected_image_path": result.get("detected_image_path"), # ADDED: detected_image_path
        "latitude": result.get("latitude") or 0.0,
        "longitude": result.get("longitude") or 0.0,
        "location": result.get("location") or "",
        "pothole_severity": result.get("pothole_severity"),
        "waste_category": result.get("waste_category"),
        "area_pct": result.get("area_pct"),
        "est_depth_m": result.get("est_depth_m"),
        "department": result.get("department") or "Unknown",
        "detection_status": result.get("detection_status") or ""
    }
    payload = {k: v for k, v in detection_payload.items() if v is not None}
    
    detection = Detection(**payload)
    db.session.add(detection)
    db.session.flush() # Flushes the new detection.id (UUID)

    # The image row logic seems redundant given the fields in Detection, 
    # but kept for compatibility if the Image model is used elsewhere.
    annotated = result.get("annotated_name")
    if annotated:
        image_row = Image(
            detection_id=detection.id, # detection.id is UUID string
            uploaded_filename=result.get("image_name") or "",
            annotated_filename=annotated,
            timestamp=datetime.utcnow()
        )
        db.session.add(image_row)

    # Department relation: map string department -> Department row + DetectionDepartment ---
    dept_name = result.get("department")
    department_obj = None
    if dept_name:
        department_obj = Department.query.filter_by(name=dept_name).first()
        if not department_obj:
            department_obj = Department(name=dept_name)
            db.session.add(department_obj)
            db.session.flush()

        # Create link row if not already present
        existing_dd = DetectionDepartment.query.filter_by(
            detection_id=detection.id,
            department_id=department_obj.id
        ).first()
        if not existing_dd:
            dd = DetectionDepartment(
                detection_id=detection.id,
                department_id=department_obj.id
            )
            db.session.add(dd)

    # Tag relations 
    # 1) Waste category as tag (if present)
    tag_names = []
    waste_cat = result.get("waste_category")
    if waste_cat:
        tag_names.append(str(waste_cat))

    # 2) Pothole severity as tag (optional, keeps schema flexible)
    pothole_sev = result.get("pothole_severity")
    if pothole_sev:
        tag_names.append(str(pothole_sev))

    # Create / link tags
    for name in tag_names:
        clean_name = name.strip()
        if not clean_name:
            continue

        tag = Tag.query.filter_by(name=clean_name).first()
        if not tag:
            tag = Tag(
                name=clean_name,
                department_id=getattr(department_obj, "id", None),
                user_id=normalized_user_id,
            )
            db.session.add(tag)
            db.session.flush()

        existing_dt = DetectionTag.query.filter_by(
            detection_id=detection.id,
            tag_id=tag.id
        ).first()
        if not existing_dt:
            dt = DetectionTag(detection_id=detection.id, tag_id=tag.id)
            db.session.add(dt)

    db.session.commit()
    return detection

def detect_image_type(image, user_id, latitude=0.0, longitude=0.0, location=""):
    if not POTHOLE_MODEL or not WASTE_MODEL:
        return None, None, None, None
    
    timestamp = int(time.time())
    original_filename = f"{timestamp}_{image.filename}"
    uid = str(timestamp)

    temp_path = os.path.join(
        current_app.config['STORAGE_FOLDER'],
        f"temp_{original_filename}"
    )
    image.save(temp_path)

    # POTHOLE DETECTION 
    pothole_results = POTHOLE_MODEL.predict(source=temp_path, conf=0.5)
    if pothole_results and len(getattr(pothole_results[0], "boxes", [])) > 0:
        original_image_path = os.path.join(current_app.config['POTHOLE_ORIGINAL_FOLDER'], original_filename)
        shutil.copy2(temp_path, original_image_path)
        annotated_filename = annotate_and_save_ultralytics(
            pothole_results,
            temp_path,
            current_app.config['POTHOLE_DETECTED_FOLDER'],
            uid
        )
        annotated_image_path = os.path.join(current_app.config['POTHOLE_DETECTED_FOLDER'], annotated_filename)

        # DEBUG PRINTS 
        print("Original image path:", original_image_path)
        print("Annotated image path:", annotated_image_path)

        pothole_info = POTHOLE_PROCESSOR.extract(temp_path, pothole_results)
        primary = pothole_info.get("primary") or {}
        record = {"type": "pothole", "params": pothole_info}
        scores = kg.reason(record)
        department = max(scores, key=scores.get)

        result = {
            "user_id": user_id,
            "image_name": original_filename,
            "image_path": _to_relative_storage(original_image_path),
            "detected_image_path": _to_relative_storage(annotated_image_path),
            "annotated_name": annotated_filename,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "pothole_severity": primary.get("class_name") or "unknown",
            "waste_category": None,
            "detection_status": f"{primary.get('class_name', 'pothole')} detected",
            "department": department,
            "area_pct": primary.get("area_pct"),
            "est_depth_m": primary.get("est_depth_m")
        }
        os.remove(temp_path)
        detection_record = save_to_database("pothole", result) 
        return "pothole", result, original_filename, original_image_path
        
    # WASTE DETECTION
    waste_results = WASTE_MODEL.predict(source=temp_path, conf=0.5)
    if waste_results and len(getattr(waste_results[0], "boxes", [])) > 0:
        original_image_path = os.path.join(current_app.config['WASTE_ORIGINAL_FOLDER'], original_filename)
        shutil.copy2(temp_path, original_image_path)
        annotated_filename = annotate_and_save_ultralytics(
            waste_results,
            temp_path,
            current_app.config['WASTE_DETECTED_FOLDER'],
            uid
        )
        annotated_image_path = os.path.join(current_app.config['WASTE_DETECTED_FOLDER'], annotated_filename)

        # DEBUG PRINTS 
        print("Original image path:", original_image_path)
        print("Annotated image path:", annotated_image_path)

        waste_info = WASTE_PROCESSOR.extract(temp_path, waste_results)
        primary = waste_info.get("primary") or {}
        category = primary.get("class_name") or "Unknown"
        record = {"type": "waste", "params": waste_info}
        scores = kg.reason(record)
        department = max(scores, key=scores.get)
        
        result = {
            "user_id": user_id,
            "image_name": original_filename,
            "image_path": _to_relative_storage(original_image_path),
            "detected_image_path": _to_relative_storage(annotated_image_path),
            "annotated_name": annotated_filename,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "pothole_severity": None,
            "waste_category": category,
            "detection_status": f"{category} detected",
            "department": department,
            "area_pct": primary.get("area_pct")
        }
        os.remove(temp_path)
        detection_record = save_to_database("waste", result)
        return "waste", result, original_filename, original_image_path

    # NO DETECTION
    os.remove(temp_path)
    result = {
        "user_id": user_id,
        "image_name": None,
        "image_path": None,
        "detected_image_path": None,
        "annotated_name": None,
        "latitude": latitude,
        "longitude": longitude,
        "location": location,
        "pothole_severity": None,
        "waste_category": None,
        "detection_status": "No detection",
        "department": None
    }
    return None, result, None, None