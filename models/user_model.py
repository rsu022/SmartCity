from datetime import datetime
from .db import db
import uuid6 as uuid 

class User(db.Model):
    __tablename__ = "user"

    # Changed from db.Integer to db.String(36) to store UUIDv7
    id = db.Column(
        db.String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid7()), 
        unique=True, 
        nullable=False
    )
    name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(50), default='user')
    organization_name = db.Column(db.String(150))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    detections = db.relationship('Detection', back_populates='user', lazy=True)
    tags = db.relationship('Tag', back_populates='user', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "organization_name": self.organization_name,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }