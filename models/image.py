from .db import db
import uuid6 as uuid 

class Image(db.Model):
    __tablename__ = 'image'

    id = db.Column(
        db.String(36), 
        primary_key=True,
        default=lambda: str(uuid.uuid7())
    )
    
    detection_id = db.Column(db.String(36), db.ForeignKey('detections.id'))
    
    uploaded_filename = db.Column(db.String, nullable=False)
    annotated_filename = db.Column(db.String, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.now())

    detection = db.relationship('Detection', back_populates='images')