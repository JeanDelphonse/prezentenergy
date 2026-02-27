#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_server.sh  —  Post-upload server setup (run inside cPanel Terminal)
#
# Run once after uploading the deployment package to the server:
#
#   bash setup_server.sh /home/<username>/<app_root> /home/<username>/virtualenv/<app_root>/3.11
#
# Arguments:
#   $1  APP_ROOT     Absolute path to the extracted application directory
#   $2  VENV_PATH    Absolute path to the virtual-env created by cPanel
#                    (visible in Setup Python App panel)
# ---------------------------------------------------------------------------

set -euo pipefail

APP_ROOT="${1:-}"
VENV_PATH="${2:-}"

# ── Validate arguments ─────────────────────────────────────────────────────
if [[ -z "${APP_ROOT}" || -z "${VENV_PATH}" ]]; then
  echo "Usage: bash setup_server.sh <APP_ROOT> <VENV_PATH>"
  echo ""
  echo "  APP_ROOT   e.g. /home/myuser/public_html/prezentenergy"
  echo "  VENV_PATH  e.g. /home/myuser/virtualenv/public_html/prezentenergy/3.11"
  exit 1
fi

if [[ ! -d "${APP_ROOT}" ]]; then
  echo "ERROR: APP_ROOT does not exist: ${APP_ROOT}"
  exit 1
fi

if [[ ! -f "${VENV_PATH}/bin/activate" ]]; then
  echo "ERROR: Virtual-env activate script not found at: ${VENV_PATH}/bin/activate"
  echo "  Create the Python app in cPanel 'Setup Python App' first, then re-run this script."
  exit 1
fi

echo "==> Activating virtual environment: ${VENV_PATH}"
# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"

echo "==> Python: $(python --version)"
echo "==> pip:    $(pip --version)"

# ── Install Python dependencies ────────────────────────────────────────────
echo ""
echo "==> Installing dependencies from requirements.txt …"
pip install --upgrade pip
pip install -r "${APP_ROOT}/requirements.txt"

# ── Create .env if it doesn't exist ───────────────────────────────────────
ENV_FILE="${APP_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ -f "${APP_ROOT}/.env.example" ]]; then
    cp "${APP_ROOT}/.env.example" "${ENV_FILE}"
    echo ""
    echo "==> Created ${ENV_FILE} from .env.example."
    echo "    IMPORTANT: Edit it now and set ANTHROPIC_API_KEY and SECRET_KEY:"
    echo "      nano ${ENV_FILE}"
  else
    echo ""
    echo "==> No .env.example found. Creating a minimal .env …"
    cat > "${ENV_FILE}" <<'ENVEOF'
ANTHROPIC_API_KEY=
FLASK_ENV=production
DATABASE_URL=sqlite:///leads.db
SECRET_KEY=
ENVEOF
    echo "    IMPORTANT: Edit ${ENV_FILE} and fill in ANTHROPIC_API_KEY and SECRET_KEY."
    echo "      nano ${ENV_FILE}"
  fi
  echo ""
  read -rp "Press Enter after you have saved your .env values to continue …"
fi

# Confirm required keys are set
ANTHROPIC_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "${ENV_FILE}" | cut -d= -f2- | tr -d '"'"'" | xargs)
SECRET_KEY=$(grep -E '^SECRET_KEY=' "${ENV_FILE}" | cut -d= -f2- | tr -d '"'"'" | xargs)

if [[ -z "${ANTHROPIC_KEY}" ]]; then
  echo "WARNING: ANTHROPIC_API_KEY is not set in .env — chatbot will not work."
fi
if [[ -z "${SECRET_KEY}" || "${SECRET_KEY}" == "change_me_to_a_random_string" ]]; then
  echo "WARNING: SECRET_KEY is not set or still placeholder in .env — set a strong random value."
fi

# ── Bootstrap the database ─────────────────────────────────────────────────
echo ""
echo "==> Initialising SQLite database …"
cd "${APP_ROOT}"
python - <<'PYEOF'
from app import create_app
app = create_app("production")
print("  Database tables created successfully.")
PYEOF

# ── Fix permissions ────────────────────────────────────────────────────────
echo ""
echo "==> Setting file permissions …"
find "${APP_ROOT}" -type f -name "*.py" -exec chmod 644 {} \;
find "${APP_ROOT}" -type d -exec chmod 755 {} \;
chmod 755 "${APP_ROOT}/passenger_wsgi.py"

# Ensure the instance directory (where SQLite writes) is writable
mkdir -p "${APP_ROOT}/instance"
chmod 755 "${APP_ROOT}/instance"

echo ""
echo "==> Setup complete!"
echo ""
echo "  Go to cPanel > Setup Python App > click 'Restart' to reload Passenger."
echo "  Then visit your domain to confirm the site is live."
