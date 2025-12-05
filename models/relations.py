from .db import db
import uuid6 as uuid 

class DetectionDepartment(db.Model):
    __tablename__ = 'detection_department'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid7()))
    detection_id = db.Column(db.String(36), db.ForeignKey('detections.id'), nullable=False)
    department_id = db.Column(db.String(36), db.ForeignKey('department.id'), nullable=False) 
    detection = db.relationship("Detection", back_populates="departments")
    department = db.relationship("Department", back_populates="detection_departments")

class DetectionTag(db.Model):
    __tablename__ = 'detection_tag'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid7()))
    detection_id = db.Column(db.String(36), db.ForeignKey('detections.id'), nullable=False) 
    tag_id = db.Column(db.String(36), db.ForeignKey('tag.id'), nullable=False) 
    detection = db.relationship('Detection', back_populates='tags')
    tag = db.relationship('Tag', back_populates='detection_tags')