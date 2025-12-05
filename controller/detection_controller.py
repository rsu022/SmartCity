import os
from flask import Blueprint, request, jsonify, current_app 
from werkzeug.utils import secure_filename 
from models.db import db
from services.detection_service import detect_image_type 
from controller.auth.auth_middleware import token_required
from models.user_model import User
from models.detection import Detection
from datetime import datetime
from sqlalchemy import select 
from sqlalchemy.orm import joinedload, selectinload 

detection_bp = Blueprint('detection_bp', __name__, url_prefix='/detections')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# POST — Detect and Save
@detection_bp.route('/', methods=['POST'])
@token_required
def create_detection(current_user):
    image = request.files.get('image')
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    location = request.form.get('location')
    
    if not image or not lat or not lon or not location:
        return jsonify({'error': 'Missing required fields (image, latitude, longitude, or location)'}), 400
    
    if image.filename == '':
        return jsonify({'error': 'No file selected for upload'}), 400
        
    if not allowed_file(image.filename):
        return jsonify({'error': 'Image file type not allowed'}), 400
        
    try:
        latitude = float(lat)
        longitude = float(lon)
    except ValueError:
        return jsonify({'error': 'Invalid latitude/longitude'}), 400
    detection_type, result_data, image_name, actual_image_path = detect_image_type(
        image, current_user.id, latitude, longitude, location
    ) 
    
    if detection_type is None:
        # If no detection is found, the service has cleaned up its temporary files
        return jsonify({'message': 'No pothole or waste detected, file discarded.'}), 200
        
    if not image_name or not actual_image_path:
        return jsonify({'error': 'Detection successful, but failed to retrieve saved file path from service.'}), 500
    

    # Save detection record to DB
    new_detection = Detection.query.filter_by(image_name=image_name, user_id=current_user.id).first()
    
    if not new_detection:
         return jsonify({'error': 'Failed to retrieve newly created detection record.'}), 500
         
    result_data.update({
        "id": new_detection.id, 
        # Latitude, longitude, location are already in result_data from service
        "user": {
            "id": current_user.id,
            "name": getattr(current_user, 'name', None),
            "email": current_user.email,
            "role": getattr(current_user, 'role', None),
            "organization_name": getattr(current_user, 'organization_name', None)
        }
    })

    return jsonify({
        'message': f'{detection_type.capitalize()} detected successfully.',
        'data': result_data
    }), 201

# GET — All detections(current user detections only)
@detection_bp.route('/my', methods=['GET'])
@token_required
def get_my_detections(current_user):
    records = Detection.query.filter(Detection.user_id == current_user.id).all()
    if not records:
        return jsonify({'message': 'No detections found for this user'}), 200
    return jsonify([r.to_dict() for r in records]), 200


#  GET — All by type(like pthole/waste) for current user
@detection_bp.route('/type/<string:detection_type>', methods=['GET'])
@token_required
def get_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400
    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
    return jsonify([r.to_dict() for r in records]), 200


# GET — single detection by id of the image for current user
@detection_bp.route('/my/<string:id>', methods=['GET'])
@token_required
def get_my_single(current_user, id): 
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first_or_404()
    
    # Get base detection data with all fields from database
    result = record.to_dict()
    
    return jsonify(result), 200


#GET= detectins by user using user_id 
@detection_bp.route("/user/<string:user_id>", methods=["GET"])
@token_required
def get_detections_by_user(current_user, user_id): 
    stmt = (
        select(Detection)
        .where(Detection.user_id == user_id)
        .options(joinedload(Detection.user)) 
        .order_by(Detection.timestamp.desc())
    )
    records = db.session.execute(stmt).scalars().all() 
    if not records:
        return jsonify({"message": "No detections found for this user"}), 404
    data = []
    for det in records:
        user = det.user         
        det_dict = {
            "id": det.id,
            "detection_type": det.detection_type,
            "image_name": det.image_name,
            "image_path": det.image_path,
            "detected_image_path": det.detected_image_path,
            "latitude": det.latitude,
            "longitude": det.longitude,
            "location": det.location,
            "detection_status": det.detection_status,
            "area_pct": det.area_pct,
            "est_depth_m": det.est_depth_m,
            "pothole_severity": det.pothole_severity,
            "waste_category": det.waste_category,
            "user": {
                "id": user.id,
                "name": getattr(user, 'name', None),
                "email": user.email,
                "role": getattr(user, 'role', None),
                "organization_name": getattr(user, 'organization_name', None)
            }
        }
        data.append(det_dict)

    return jsonify({"detections": data}), 200


# GET — Full user details with detections (admin only)
@detection_bp.route("/user/details/<string:user_id>", methods=["GET"])
@token_required
def get_user_full_details(current_user, user_id):
    if getattr(current_user, "role", "user") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    user = (
        User.query.options(
            joinedload(User.detections)
            .joinedload(Detection.departments)
            .joinedload("department"),
            joinedload(User.detections)
            .joinedload(Detection.tags)
            .joinedload("tag")
        )
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "organization_name": user.organization_name,
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "detections": []
    }
    for det in user.detections:
        # Assuming Detection.departments and Detection.tags are relationships
        departments = [dept.department.name for dept in det.departments if hasattr(dept, 'department') and dept.department]
        tags = [tag.tag.name for tag in det.tags if hasattr(tag, 'tag') and tag.tag]
        
        data["detections"].append({
            "id": det.id,
            "detection_type": det.detection_type,
            "image_name": det.image_name,
            "latitude": det.latitude,
            "longitude": det.longitude,
            "location": det.location,
            "timestamp": det.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "detection_status": det.detection_status,
            "departments": departments,
            "tags": tags
        })

    return jsonify(data), 200


#PUT — Update detection location for current user
@detection_bp.route('/my/update/<string:id>', methods=['PUT'])
@token_required
def update_my_detection(current_user, id):
    data = request.json
    new_location = data.get('location')
    if not new_location:
        return jsonify({'error': 'Location is required'}), 400
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    record.location = new_location
    db.session.commit()
    return jsonify({
        'message': f'{record.detection_type.capitalize()} location updated',
        'data': {
            'id': record.id,
            'detection_type': record.detection_type,
            'image_name': record.image_name,
            'image_path': record.image_path,
            'detected_image_path': record.detected_image_path,
            'latitude': record.latitude,
            'longitude': record.longitude,
            'location': record.location,
            'timestamp': record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'detection_status': record.detection_status
        }
    }), 200

# DELETE — Delete detection by id for current user
@detection_bp.route('/my/<string:id>', methods=['DELETE'])
@token_required
def delete_my_detection(current_user, id):
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404
        
    # The image path handling is tricky as the folder is determined by detection type
    # but the path is saved in the record. We rely on the saved paths first.
    
    original_path_to_delete = record.image_path
    annotated_path_to_delete = record.detected_image_path
    
    # Try to delete original image
    if original_path_to_delete and os.path.exists(original_path_to_delete):
        os.remove(original_path_to_delete)
        
    # Try to delete annotated image
    if annotated_path_to_delete and os.path.exists(annotated_path_to_delete):
        os.remove(annotated_path_to_delete)
            
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': f'{record.detection_type.capitalize()} deleted successfully'}), 200


# DELETE — Delete all detections by type for current user
@detection_bp.route('/my/type/<string:detection_type>', methods=['DELETE'])
@token_required
def delete_all_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400
        
    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
        
    for record in records:
        original_path_to_delete = record.image_path
        annotated_path_to_delete = record.detected_image_path
        
        # Try to delete original image
        if original_path_to_delete and os.path.exists(original_path_to_delete):
            os.remove(original_path_to_delete)
        
        # Try to delete annotated image
        if annotated_path_to_delete and os.path.exists(annotated_path_to_delete):
            os.remove(annotated_path_to_delete)
                
        db.session.delete(record)
        
    db.session.commit()
    return jsonify({
        "message": f"All {detection_type} records deleted successfully.",
        "count": len(records)
    }), 200