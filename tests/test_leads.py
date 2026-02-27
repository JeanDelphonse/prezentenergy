import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from extensions import db as _db


@pytest.fixture
def app():
    app = create_app("development")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_submit_lead_minimal(client):
    res = client.post(
        "/api/leads",
        data=json.dumps({"full_name": "Jane Doe", "email": "jane@example.com"}),
        content_type="application/json",
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "id" in data


def test_submit_lead_full(client):
    payload = {
        "full_name": "John Fleet",
        "email": "john@cityfleet.gov",
        "phone": "408-555-1234",
        "company_name": "San Jose City Fleet",
        "industry_segment": "City Vehicle Fleet",
        "fleet_size": "50",
        "location_zip": "95101",
        "current_charging_status": "Zero Infrastructure",
        "primary_interests": ["Zero CapEx Subscription (CaaS)", "Carbon Reduction Reporting"],
        "timeline": "1–3 months",
        "comments": "Testing V2G compatibility for our Chevy Bolts.",
    }
    res = client.post(
        "/api/leads",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 201


def test_submit_lead_missing_required(client):
    res = client.post(
        "/api/leads",
        data=json.dumps({"full_name": "No Email"}),
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_list_leads(client):
    # Create one first
    client.post(
        "/api/leads",
        data=json.dumps({"full_name": "Test User", "email": "test@x.com"}),
        content_type="application/json",
    )
    res = client.get("/api/leads")
    assert res.status_code == 200
    leads = res.get_json()
    assert isinstance(leads, list)
    assert len(leads) == 1
    assert leads[0]["email"] == "test@x.com"


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Prezent" in res.data
    assert b"VoltBot" in res.data
