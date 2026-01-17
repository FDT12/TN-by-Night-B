# backend/models.py
from db import db
from datetime import datetime


class User(db.Model):
    """User model for authentication"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")  # 'user', 'admin'
    okta_user_id = db.Column(db.String(100), nullable=True) # For 2FA mapping
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username}>"


class Event(db.Model):
    """Event model for storing scraped and suggested events"""
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    place = db.Column(db.String(300))
    date = db.Column(db.String(200))
    price = db.Column(db.String(100))
    url = db.Column(db.String(500), unique=True, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    
    # New fields for suggestions
    status = db.Column(db.String(20), default="approved") # 'approved', 'pending', 'rejected'
    suggested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert event to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'place': self.place,
            'date': self.date,
            'price': self.price,
            'url': self.url,
            'city': self.city,
            'status': self.status,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Event {self.id}: {self.name[:50]}>"
