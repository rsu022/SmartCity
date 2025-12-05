import os
import time
from datetime import datetime
from flask import current_app
# Assuming these utility and model imports are correctly defined elsewhere
from utils.viz import annotate_and_save_ultralytics
from reasoning.kg_gnn import KnowledgeGraphReasoner
from models import (
    db,
    Detection,
    Image,
    Department,
    Tag,
    DetectionDepartment,
    DetectionTag
)

# NOTE: The ModelLoader is typically initialized outside this class (e.g., in __init__) 
# or accessed via current_app if running in a Flask context.
class InferenceService:
    def __init__(self, model_loader):
        self.model_loader = model_loader
        self.reasoner = KnowledgeGraphReasoner()
    
    def save_detection_to_db(self, user_id, image_path, annotated_path, task_type, detections, department_scores):
        """
        Saves detection results, image paths, and associated metadata (department, tags) 
        to the database.
        """
        try:  
            # 1. Determine the highest-scoring department
            department_name = (
                max(department_scores, key=department_scores.get)
                if department_scores else None
            )
            
            # 2. Get the detected class name (e.g., "Small Pothole" or "Plastic Bag")
            class_name = None
            if detections and "class_id" in detections[0]:
                class_name = self.model_loader.get_class_name(
                    task_type,
                    detections[0]["class_id"]
                )
            
            # 3. Create the main Detection record
            det = Detection(
                user_id=user_id,
                detection_type=task_type,
                image_name=os.path.basename(image_path),
                latitude=0.0,
                longitude=0.0,
                location="",
                timestamp=datetime.utcnow(),
                pothole_severity=class_name if task_type == "pothole" else None,
                waste_category=class_name if task_type == "waste" else None,
                department=department_name,
                detection_status=f"{class_name} detected" if class_name else "detected"
            )

            db.session.add(det)
            # Flush session to populate det.id before related objects are created
            db.session.flush()

            # 4. Create the Image record
            img = Image(
                detection_id=det.id, 
                uploaded_filename=os.path.basename(image_path),
                annotated_filename=os.path.basename(annotated_path),
                timestamp=datetime.utcnow()
            )
            db.session.add(img)

            # 5. Handle Department association (DetectionDepartment)
            dept = None
            if department_name:
                # Find existing department or create a new one
                dept = Department.query.filter_by(name=department_name).first()

                if not dept:
                    dept = Department(name=department_name)
                    db.session.add(dept)
                    db.session.flush()

                rel = DetectionDepartment(
                    detection_id=det.id, 
                    department_id=dept.id
                )
                db.session.add(rel)

            # 6. Handle Tag association (DetectionTag)
            if class_name:
                # Find existing tag or create a new one
                tag = Tag.query.filter_by(name=class_name).first()

                if not tag:
                    # Associate the tag with the detected department if available
                    tag = Tag(
                        name=class_name,
                        department_id=dept.id if dept else None,
                        user_id=user_id
                    )
                    db.session.add(tag)
                    db.session.flush()

                tag_rel = DetectionTag(
                    detection_id=det.id, 
                    tag_id=tag.id
                )
                db.session.add(tag_rel)
                
            db.session.commit()
            print("Saved Detection + Department + Tag (ID:", det.id, ")")
            return True
        except Exception as e:
            db.session.rollback()
            # Log the error properly in a real application
            print("DB Save Error:", e)
            return False
            
    def run(self, image_path, user_id, task_type="waste"):
        """
        Runs the entire inference pipeline: detection -> annotation -> reasoning -> database save.
        """
        start = time.time()
        try:
            # 1. Run detection model
            results = self.model_loader.predict(image_path, task_type)
            detections = []
            
            # Extract structured detection data
            if results and results[0].boxes and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    detections.append({
                        "bbox": box.xyxy.tolist()[0],
                        "confidence": float(box.conf[0]),
                        "class_id": int(box.cls[0])
                    })
            
            # 2. Save annotated image
            # Generate a unique identifier for the annotated image file
            # Using current timestamp as a simple unique ID
            uid = str(int(time.time())) 
            annotated_dir = current_app.config["ANNOTATED_FOLDER"]
            annotated_path = annotate_and_save_ultralytics(
                results, image_path, annotated_dir, uid
            )
            
            # 3. Prepare data for reasoning (GNN input)
            area_pct = 0
            class_name = ""
            
            if len(detections) > 0:
                # Assuming first detection is the primary one for GNN input
                first_box = results[0].boxes[0]
                xyxy = first_box.xyxy[0]
                # Calculate area percentage (normalized to original image dimensions)
                w = float(xyxy[2] - xyxy[0])
                h = float(xyxy[3] - xyxy[1])
                box_area = w * h
                img_h, img_w = results[0].orig_img.shape[:2]
                image_area = img_h * img_w
                area_pct = box_area / image_area
                
                class_name = self.model_loader.get_class_name(
                    task_type,
                    int(first_box.cls[0])
                )
            
            # 4. Run Reasoning (GNN)
            gnn_input = {
                "type": task_type,
                "params": {
                    "primary": {
                        "area_pct": area_pct,
                        "class_name": class_name,
                        "est_depth_m": 0.10 if task_type == "pothole" else 0
                    }
                }
            }
            department_scores = self.reasoner.reason(gnn_input)

            # 5. Save to Database
            self.save_detection_to_db(
                user_id=user_id,
                image_path=image_path,
                annotated_path=annotated_path,
                task_type=task_type,
                detections=detections,
                department_scores=department_scores
            )
            
            return {
                "success": True,
                "task_type": task_type,
                "detections": detections,
                "annotated_path": annotated_path,
                "department_scores": department_scores,
                "execution_time": round(time.time() - start, 3),
            }
        except Exception as e:
            # Log the full traceback in a real application
            print("INFERENCE ERROR:", e)
            return {
                "success": False,
                "task_type": task_type,
                "error": str(e)
            }