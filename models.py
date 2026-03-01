from datetime import datetime
from flask_login import UserMixin
from extensions import db


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)

    # Primary Contact
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)

    # Organization
    company_name = db.Column(db.String(150), nullable=True)
    industry_segment = db.Column(db.String(60), nullable=True)
    # Options: City Vehicle Fleet | Business Campus / Workplace |
    #          Residential Complex / Multi-Unit Dwelling | Hotel / Hospitality

    # Operational
    fleet_size = db.Column(db.String(30), nullable=True)
    location_zip = db.Column(db.String(20), nullable=True)
    current_charging_status = db.Column(db.String(60), nullable=True)
    # Options: Zero Infrastructure | Fixed Chargers (Insufficient) | Planning Phase

    # Strategic interests (comma-separated)
    primary_interests = db.Column(db.Text, nullable=True)
    # Options: Employee Productivity / Time Savings | Virtual Power Plant (VPP) / Grid Support Revenue |
    #          Zero CapEx Subscription (CaaS) | Carbon Reduction Reporting

    # Intent
    timeline = db.Column(db.String(60), nullable=True)
    # Options: Within 1 week | 1-3 months | Budgeting for 2027
    comments = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "company_name": self.company_name,
            "industry_segment": self.industry_segment,
            "fleet_size": self.fleet_size,
            "location_zip": self.location_zip,
            "current_charging_status": self.current_charging_status,
            "primary_interests": self.primary_interests,
            "timeline": self.timeline,
            "comments": self.comments,
            "created_at": self.created_at.isoformat(),
        }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    organization = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    additional_info = db.Column(db.Text, nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    verification_codes = db.relationship(
        "VerificationCode", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class VerificationCode(db.Model):
    __tablename__ = "verification_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    # purpose: 'register' | 'login' | 'settings'
    purpose = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
