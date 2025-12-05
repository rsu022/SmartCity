from .db import db
import uuid6 as uuid 

class Department(db.Model):
    __tablename__ = 'department'

    id = db.Column(
        db.String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid7()),
        unique=True, 
        nullable=False
    )
    name = db.Column(db.String(100), unique=True, nullable=False)

    tags = db.relationship('Tag', back_populates='department', lazy=True)
    detection_departments = db.relationship('DetectionDepartment', back_populates='department', lazy=True)