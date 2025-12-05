from .db import db
import uuid6 as uuid

class Tag(db.Model):
    __tablename__ = 'tag'

    id = db.Column(
        db.String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid7()),
        unique=True, 
        nullable=False
    )
    name = db.Column(db.String, nullable=False)
    
    department_id = db.Column(db.String(36), db.ForeignKey('department.id'), nullable=True) 

    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', back_populates='tags')
    department = db.relationship('Department', back_populates='tags')

    detection_tags = db.relationship('DetectionTag', back_populates='tag', lazy=True)