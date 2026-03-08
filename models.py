from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    stage = db.Column(db.String(50), default="Saved")  # Saved → Applied → Interview → Offer / Rejected
    date_applied = db.Column(db.String(50), default="")
    job_description = db.Column(db.Text, default="")    # We'll use this for match scoring
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)        # Plain text resume
    version = db.Column(db.Integer, default=1)          # Tracks improvements over time
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    