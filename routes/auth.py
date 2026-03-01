import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, mail
from models import User, VerificationCode

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def send_verification_code(user, purpose):
    """Generate a 6-digit code, persist it, and email it to the user."""
    code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    vc = VerificationCode(
        user_id=user.id,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
        used=False,
    )
    db.session.add(vc)
    db.session.commit()

    purpose_labels = {
        "register": "complete your registration",
        "login": "sign in to your account",
        "settings": "confirm your account changes",
    }
    label = purpose_labels.get(purpose, "verify your identity")

    msg = Message(
        subject="Prezent.Energy — Your verification code",
        recipients=[user.email],
        body=(
            f"Hi {user.full_name},\n\n"
            f"Your one-time verification code to {label} is:\n\n"
            f"    {code}\n\n"
            f"This code expires in 10 minutes. If you did not request this, "
            f"please ignore this email.\n\n"
            f"— The Prezent.Energy Team"
        ),
    )
    mail.send(msg)


def _validate_code(user_id, purpose, submitted_code):
    """Return (True, None) if valid; (False, error_message) otherwise."""
    now = datetime.utcnow()
    vc = (
        VerificationCode.query
        .filter_by(user_id=user_id, purpose=purpose, used=False)
        .filter(VerificationCode.expires_at > now)
        .order_by(VerificationCode.id.desc())
        .first()
    )
    if vc is None:
        return False, "Code expired or not found. Please request a new one."
    if vc.code != submitted_code:
        return False, "Incorrect code. Please try again."
    vc.used = True
    db.session.commit()
    return True, None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("auth/register.html")


@auth_bp.route("/register", methods=["POST"])
def register_post():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    address = request.form.get("address", "").strip()
    organization = request.form.get("organization", "").strip()
    phone = request.form.get("phone", "").strip()
    additional_info = request.form.get("additional_info", "").strip()

    if not full_name or not email or not password:
        flash("Full name, email, and password are required.", "error")
        return redirect(url_for("auth.register"))

    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.register"))

    if User.query.filter_by(email=email).first():
        flash("An account with that email already exists.", "error")
        return redirect(url_for("auth.register"))

    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        address=address,
        organization=organization,
        phone=phone,
        additional_info=additional_info,
        is_verified=False,
    )
    db.session.add(user)
    db.session.commit()

    send_verification_code(user, "register")
    session["pending_user_id"] = user.id
    session["verify_purpose"] = "register"
    return redirect(url_for("auth.verify"))


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

@auth_bp.route("/verify", methods=["GET"])
def verify():
    if "pending_user_id" not in session:
        return redirect(url_for("auth.login"))
    purpose = session.get("verify_purpose", "login")
    return render_template("auth/verify.html", purpose=purpose)


@auth_bp.route("/verify", methods=["POST"])
def verify_post():
    user_id = session.get("pending_user_id")
    purpose = session.get("verify_purpose", "login")

    if not user_id:
        flash("Session expired. Please start again.", "error")
        return redirect(url_for("auth.login"))

    submitted = request.form.get("code", "").strip()
    ok, err = _validate_code(user_id, purpose, submitted)

    if not ok:
        flash(err, "error")
        return redirect(url_for("auth.verify"))

    user = User.query.get(user_id)

    if purpose == "register":
        user.is_verified = True
        db.session.commit()
        login_user(user)
        session.pop("pending_user_id", None)
        session.pop("verify_purpose", None)
        flash("Account verified! Welcome to Prezent.Energy.", "success")
        return redirect(url_for("main.index"))

    elif purpose == "login":
        login_user(user)
        session.pop("pending_user_id", None)
        session.pop("verify_purpose", None)
        flash("Signed in successfully.", "success")
        return redirect(url_for("main.index"))

    elif purpose == "settings":
        # Apply pending profile changes stored in session
        pending = session.pop("pending_profile", {})
        if pending.get("full_name"):
            user.full_name = pending["full_name"]
        if "address" in pending:
            user.address = pending["address"]
        if "organization" in pending:
            user.organization = pending["organization"]
        if "phone" in pending:
            user.phone = pending["phone"]
        if "additional_info" in pending:
            user.additional_info = pending["additional_info"]
        if pending.get("new_password"):
            user.password_hash = generate_password_hash(pending["new_password"])
        db.session.commit()
        session.pop("pending_user_id", None)
        session.pop("verify_purpose", None)
        flash("Account updated successfully.", "success")
        return redirect(url_for("auth.account"))

    flash("Unknown verification purpose.", "error")
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("auth/login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    send_verification_code(user, "login")
    session["pending_user_id"] = user.id
    session["verify_purpose"] = "login"
    return redirect(url_for("auth.verify"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Account / Profile
# ---------------------------------------------------------------------------

@auth_bp.route("/account", methods=["GET"])
@login_required
def account():
    return render_template("auth/account.html", user=current_user)


@auth_bp.route("/account", methods=["POST"])
@login_required
def account_post():
    """Stage profile changes in session, then require 2FA before saving."""
    full_name = request.form.get("full_name", "").strip()
    address = request.form.get("address", "").strip()
    organization = request.form.get("organization", "").strip()
    phone = request.form.get("phone", "").strip()
    additional_info = request.form.get("additional_info", "").strip()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password and new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("auth.account"))

    session["pending_profile"] = {
        "full_name": full_name,
        "address": address,
        "organization": organization,
        "phone": phone,
        "additional_info": additional_info,
        "new_password": new_password if new_password else None,
    }
    send_verification_code(current_user, "settings")
    session["pending_user_id"] = current_user.id
    session["verify_purpose"] = "settings"
    return redirect(url_for("auth.verify"))
