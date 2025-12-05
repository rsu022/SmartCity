import uuid
from models import db
from models.user import User
from models.department import Department
from models.tag import Tag
from models.image import Image
from models.detection import Detection
from models.relations import DetectionDepartment, DetectionTag

def create_detection_with_relations(
    det_id,
    det_type,
    user_id,
    params,
    routing,
    uploaded_filename,
    annotated_filename,
):
    detection = Detection(
        id=det_id,
        user_id=user_id,
        type=det_type,
        params=params,
        routing=routing,
        timestamp=params.get("timestamp") or "",
    )
    db.session.add(detection)

    image = Image(
        id=str(uuid.uuid4()),
        detection_id=det_id,
        uploaded_filename=uploaded_filename,
        annotated_filename=annotated_filename,
        timestamp=params.get("timestamp") or "",
    )
    db.session.add(image)

    assigned_departments = routing.get("departments", [])
    for dept_name in assigned_departments:
        dept = Department.query.filter_by(name=dept_name).first()
        if dept:
            link = DetectionDepartment(
                detection_id=det_id,
                department_id=dept.id
            )
            db.session.add(link)

    auto_tag_names = []
    if det_type == "waste":
        auto_tag_names = ["waste", "garbage", "trash"]
    elif det_type == "pothole":
        auto_tag_names = ["pothole", "road_damage"]

    for tag_name in auto_tag_names:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag:
            link = DetectionTag(
                detection_id=det_id,
                tag_id=tag.id
            )
            db.session.add(link)

    db.session.commit()

    return detection
