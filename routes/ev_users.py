from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import EVUser

ev_users_bp = Blueprint("ev_users", __name__, url_prefix="/settings")


@ev_users_bp.route("/ev-users")
@login_required
def dashboard():
    sort = request.args.get("sort", "full_name")
    if sort not in ("full_name", "license_plate"):
        sort = "full_name"

    ev_users = (
        EVUser.query.filter_by(user_id=current_user.id)
        .order_by(getattr(EVUser, sort))
        .all()
    )
    return render_template("ev_users.html", ev_users=ev_users, sort=sort)


@ev_users_bp.route("/ev-users/add", methods=["POST"])
@login_required
def add():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    car_make = request.form.get("car_make", "").strip()
    car_model = request.form.get("car_model", "").strip()
    license_plate = request.form.get("license_plate", "").strip()

    if not all([full_name, email, phone, car_make, car_model, license_plate]):
        flash("All fields are required.", "error")
        return redirect(url_for("ev_users.dashboard"))

    ev_user = EVUser(
        user_id=current_user.id,
        full_name=full_name,
        email=email,
        phone=phone,
        car_make=car_make,
        car_model=car_model,
        license_plate=license_plate,
    )
    db.session.add(ev_user)
    db.session.commit()
    flash(f"{full_name} has been added to your EV fleet.", "success")
    return redirect(url_for("ev_users.dashboard"))


@ev_users_bp.route("/ev-users/<int:ev_user_id>/edit", methods=["POST"])
@login_required
def edit(ev_user_id):
    ev_user = EVUser.query.filter_by(id=ev_user_id, user_id=current_user.id).first_or_404()

    ev_user.full_name = request.form.get("full_name", ev_user.full_name).strip()
    ev_user.email = request.form.get("email", ev_user.email).strip()
    ev_user.phone = request.form.get("phone", ev_user.phone).strip()
    ev_user.car_make = request.form.get("car_make", ev_user.car_make).strip()
    ev_user.car_model = request.form.get("car_model", ev_user.car_model).strip()
    ev_user.license_plate = request.form.get("license_plate", ev_user.license_plate).strip()

    db.session.commit()
    flash(f"{ev_user.full_name}'s record has been updated.", "success")
    return redirect(url_for("ev_users.dashboard"))


@ev_users_bp.route("/ev-users/<int:ev_user_id>/delete", methods=["POST"])
@login_required
def delete(ev_user_id):
    ev_user = EVUser.query.filter_by(id=ev_user_id, user_id=current_user.id).first_or_404()
    name = ev_user.full_name
    db.session.delete(ev_user)
    db.session.commit()
    flash(f"{name} has been removed from your EV fleet.", "success")
    return redirect(url_for("ev_users.dashboard"))
