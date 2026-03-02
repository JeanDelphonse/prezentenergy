from flask import Blueprint, render_template, jsonify, request, current_app

import requests

from agents.industry_news_agent import get_industry_news, is_loading

news_bp = Blueprint("news", __name__)


@news_bp.route("/news")
def news_page():
    # Trigger background fetch if cache is cold — page renders instantly
    get_industry_news()
    maps_key = current_app.config.get("GOOGLE_MAPS_API_KEY", "")
    return render_template("news.html", maps_key=maps_key)


@news_bp.route("/api/industry-news")
def industry_news_api():
    force = request.args.get("refresh") == "1"
    news, regulations = get_industry_news(force_refresh=force)
    return jsonify({
        "news": news,
        "regulations": regulations,
        "loading": is_loading(),
    })


@news_bp.route("/api/charging-stations")
def charging_stations():
    """
    Proxy endpoint for DC fast-charging station lookup.

    Accepts:
      ?lat=X&lng=Y            (coordinates)
      ?zip=XXXXX              (US zip code — geocoded via Nominatim)
      &radius=<miles>         (optional, default 25)

    Returns OpenChargeMap Level-3 stations as JSON.
    """
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    zipcode = request.args.get("zip", "").strip()
    radius = request.args.get("radius", 25)

    # ── Zip → lat/lng via Nominatim (OSM) ────────────────────────────────────
    if zipcode and not (lat and lng):
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": zipcode,
                    "format": "json",
                    "countrycodes": "us",
                    "limit": 1,
                },
                headers={"User-Agent": "PrezentEnergy-StationFinder/1.0"},
                timeout=8,
            )
            results = r.json()
            if results:
                lat = results[0]["lat"]
                lng = results[0]["lon"]
            else:
                return jsonify({"error": "Zip code not found"}), 404
        except Exception as exc:
            return jsonify({"error": f"Geocoding failed: {exc}"}), 500

    if not (lat and lng):
        return jsonify({"error": "Provide lat/lng or zip"}), 400

    # ── OpenChargeMap — Level 3 (DC fast charge) ─────────────────────────────
    try:
        r = requests.get(
            "https://api.openchargemap.io/v3/poi/",
            params={
                "output": "json",
                "latitude": lat,
                "longitude": lng,
                "distance": radius,
                "distanceunit": "miles",
                "levelid": 3,
                "maxresults": 30,
                "compact": True,
                "verbose": False,
            },
            headers={"User-Agent": "PrezentEnergy-StationFinder/1.0"},
            timeout=10,
        )
        r.raise_for_status()
        stations = []
        for s in r.json():
            addr = s.get("AddressInfo", {})
            station_lat = addr.get("Latitude")
            station_lng = addr.get("Longitude")
            if station_lat is None or station_lng is None:
                continue
            stations.append(
                {
                    "name": addr.get("Title", "EV Charging Station"),
                    "lat": station_lat,
                    "lng": station_lng,
                    "address": addr.get("AddressLine1", ""),
                    "city": addr.get("Town", ""),
                    "state": addr.get("StateOrProvince", ""),
                }
            )
        return jsonify(
            {
                "stations": stations,
                "center": {"lat": float(lat), "lng": float(lng)},
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
