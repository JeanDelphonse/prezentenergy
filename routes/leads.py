from flask import Blueprint, request, jsonify
from extensions import db
from models import Lead

leads_bp = Blueprint("leads", __name__)


@leads_bp.route("/leads", methods=["POST"])
def submit_lead():
    data = request.get_json(silent=True) or request.form.to_dict()

    if not data.get("full_name") or not data.get("email"):
        return jsonify({"error": "full_name and email are required"}), 400

    # Normalise multi-value interests list → comma-separated string
    interests = data.get("primary_interests", "")
    if isinstance(interests, list):
        interests = ", ".join(interests)

    lead = Lead(
        full_name=data.get("full_name", "").strip(),
        email=data.get("email", "").strip().lower(),
        phone=data.get("phone", "").strip() or None,
        company_name=data.get("company_name", "").strip() or None,
        industry_segment=data.get("industry_segment") or None,
        fleet_size=data.get("fleet_size", "").strip() or None,
        location_zip=data.get("location_zip", "").strip() or None,
        current_charging_status=data.get("current_charging_status") or None,
        primary_interests=interests or None,
        timeline=data.get("timeline") or None,
        comments=data.get("comments", "").strip() or None,
    )

    db.session.add(lead)
    db.session.commit()

    return jsonify({"success": True, "id": lead.id}), 201


@leads_bp.route("/leads", methods=["GET"])
def list_leads():
    """Simple admin endpoint — protect with auth in production."""
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return jsonify([l.to_dict() for l in leads])
