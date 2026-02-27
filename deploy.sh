#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh  —  Build a deployment package for GoDaddy cPanel
#
# Usage:
#   bash deploy.sh
#
# Output:
#   prezentenergy-deploy.zip  (ready to upload via cPanel File Manager or FTP)
# ---------------------------------------------------------------------------

set -euo pipefail

APP_NAME="prezentenergy"
ARCHIVE="${APP_NAME}-deploy.zip"

echo "==> Building deployment package: ${ARCHIVE}"

# ── Sanity checks ──────────────────────────────────────────────────────────
if ! command -v zip &>/dev/null; then
  echo "ERROR: 'zip' is required. Install it (e.g. via Git Bash on Windows) and retry."
  exit 1
fi

# ── Warn if .env has placeholder values ────────────────────────────────────
if grep -q "change_me" .env 2>/dev/null; then
  echo "WARNING: .env still contains placeholder values. Update SECRET_KEY before deploying."
fi

# ── Create the archive ─────────────────────────────────────────────────────
# Remove a stale archive if one exists
rm -f "${ARCHIVE}"

zip -r "${ARCHIVE}" . \
  --exclude "*.pyc" \
  --exclude "__pycache__/*" \
  --exclude ".venv/*" \
  --exclude "venv/*" \
  --exclude "env/*" \
  --exclude ".git/*" \
  --exclude ".gitignore" \
  --exclude "instance/*" \
  --exclude "*.db" \
  --exclude "*.sqlite3" \
  --exclude ".env" \
  --exclude "static/video/*" \
  --exclude "${ARCHIVE}" \
  --exclude "DEPLOY.md"

echo ""
echo "==> Done. Package: ${ARCHIVE}  ($(du -sh "${ARCHIVE}" | cut -f1))"
echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo " NEXT STEPS — GoDaddy cPanel Deployment"
echo "──────────────────────────────────────────────────────────────────────"
echo ""
echo " 1. Log in to your GoDaddy cPanel account."
echo ""
echo " 2. Under 'Files', open 'File Manager'."
echo "    - Navigate to your domain root (e.g. public_html/) or a subdirectory."
echo "    - Upload ${ARCHIVE} and extract it there."
echo "    - The extracted folder should contain app.py, passenger_wsgi.py, etc."
echo ""
echo " 3. Under 'Software', open 'Setup Python App'."
echo "    - Click 'CREATE APPLICATION'."
echo "    - Python version  : 3.11 (or latest available)"
echo "    - Application root: the directory where you extracted the zip"
echo "      (e.g.  prezentenergy  if extracted inside public_html)"
echo "    - Application URL : your domain or subdomain"
echo "    - Startup file    : passenger_wsgi.py"
echo "    - Application entry point: application"
echo "    - Click 'CREATE'."
echo ""
echo " 4. In the Python App panel, click 'Run Pip Install' and point it at"
echo "    requirements.txt  — OR — open the Terminal (cPanel > Advanced >"
echo "    Terminal) and run:"
echo "      source <venv_path>/bin/activate"
echo "      pip install -r <app_root>/requirements.txt"
echo ""
echo " 5. Still in Terminal, create the .env file:"
echo "      cd <app_root>"
echo "      cp .env.example .env"
echo "      nano .env          # fill in ANTHROPIC_API_KEY and SECRET_KEY"
echo ""
echo " 6. Initialise the database:"
echo "      python -c \"from app import create_app; create_app('production')\""
echo "    (This runs db.create_all() and creates instance/leads.db.)"
echo ""
echo " 7. Back in 'Setup Python App', click 'Restart' to reload Passenger."
echo ""
echo " 8. Visit your domain — you should see the Prezent.Energy site."
echo ""
echo " TROUBLESHOOTING"
echo "   - Check  stderr.log / error_log  in cPanel Logs if the app won't start."
echo "   - Ensure the application root path in cPanel matches where files live."
echo "   - The .htaccess in the app root handles Passenger routing automatically."
echo "──────────────────────────────────────────────────────────────────────"
