/* news-map.js — Google Maps + OpenChargeMap integration for /news page */

(function () {
  "use strict";

  let map, infoWindow;
  const API_STATIONS = "/api/charging-stations";

  /* ── Bootstrap called by Google Maps callback ─────────────────────────── */
  window.initNewsMap = function () {
    const mapEl = document.getElementById("charging-map");
    if (!mapEl) return;

    map = new google.maps.Map(mapEl, {
      zoom: 12,
      center: { lat: 37.3382, lng: -121.8863 }, // San Jose default
      mapTypeId: "roadmap",
      styles: darkMapStyles(),
    });

    infoWindow = new google.maps.InfoWindow();

    // Auto-locate user
    autoLocate();

    // Zip search button
    const searchBtn = document.getElementById("map-search-btn");
    const zipInput = document.getElementById("map-zip-input");
    if (searchBtn && zipInput) {
      searchBtn.addEventListener("click", () => searchByZip(zipInput.value.trim()));
      zipInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchByZip(zipInput.value.trim());
      });
    }
  };

  /* ── Auto-locate ──────────────────────────────────────────────────────── */
  function autoLocate() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lng } = pos.coords;
        map.setCenter({ lat, lng });
        loadStations({ lat, lng });
      },
      () => {
        // Silent fallback — default center already set
      }
    );
  }

  /* ── Zip code search ──────────────────────────────────────────────────── */
  function searchByZip(zip) {
    if (!zip) return;
    const statusEl = document.getElementById("map-status");
    if (statusEl) statusEl.textContent = "Searching…";

    fetch(`${API_STATIONS}?zip=${encodeURIComponent(zip)}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          if (statusEl) statusEl.textContent = data.error;
          return;
        }
        if (statusEl) statusEl.textContent = "";
        map.setCenter(data.center);
        map.setZoom(12);
        plotStations(data.stations);
      })
      .catch(() => {
        if (statusEl) statusEl.textContent = "Could not load stations. Try again.";
      });
  }

  /* ── Load stations by coordinates ────────────────────────────────────── */
  function loadStations({ lat, lng }) {
    fetch(`${API_STATIONS}?lat=${lat}&lng=${lng}`)
      .then((r) => r.json())
      .then((data) => {
        if (!data.error) plotStations(data.stations);
      })
      .catch(() => {});
  }

  /* ── Plot markers ────────────────────────────────────────────────────── */
  let markers = [];

  function clearMarkers() {
    markers.forEach((m) => m.setMap(null));
    markers = [];
  }

  function plotStations(stations) {
    clearMarkers();
    stations.forEach((s) => {
      const marker = new google.maps.Marker({
        position: { lat: s.lat, lng: s.lng },
        map,
        title: s.name,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 9,
          fillColor: "#22c55e",
          fillOpacity: 0.9,
          strokeColor: "#15803d",
          strokeWeight: 2,
        },
      });

      marker.addListener("click", () => {
        infoWindow.setContent(
          `<div style="color:#111;font-family:Inter,sans-serif;max-width:200px;">
            <strong>${s.name}</strong><br/>
            ${s.address ? s.address + "<br/>" : ""}
            ${s.city ? s.city + (s.state ? ", " + s.state : "") : ""}
            <br/><span style="color:#15803d;font-size:12px;">⚡ DC Fast Charge (Level 3)</span>
          </div>`
        );
        infoWindow.open(map, marker);
      });

      markers.push(marker);
    });
  }

  /* ── Dark map style ──────────────────────────────────────────────────── */
  function darkMapStyles() {
    return [
      { elementType: "geometry", stylers: [{ color: "#0a0f1a" }] },
      { elementType: "labels.text.stroke", stylers: [{ color: "#0a0f1a" }] },
      { elementType: "labels.text.fill", stylers: [{ color: "#9ca3af" }] },
      {
        featureType: "road",
        elementType: "geometry",
        stylers: [{ color: "#1f2937" }],
      },
      {
        featureType: "road.arterial",
        elementType: "geometry",
        stylers: [{ color: "#374151" }],
      },
      {
        featureType: "road.highway",
        elementType: "geometry",
        stylers: [{ color: "#4b5563" }],
      },
      {
        featureType: "water",
        elementType: "geometry",
        stylers: [{ color: "#111827" }],
      },
      {
        featureType: "poi",
        elementType: "geometry",
        stylers: [{ color: "#111827" }],
      },
      {
        featureType: "transit",
        elementType: "geometry",
        stylers: [{ color: "#1f2937" }],
      },
    ];
  }
})();
