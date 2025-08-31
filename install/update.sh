#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/GaseraWebUI"

# Require root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo $0)"
  exit 1
fi

echo "🔄 Updating deployed code in $APP_DIR..."
cd "$APP_DIR"

echo "Resetting local changes..."
git reset --hard

echo "Pulling latest from origin/main..."
git pull --ff-only origin main || {
  echo "❌ Git pull failed!"
  exit 1
}

echo "🔧 Normalizing script permissions..."
# Keep *.sh executable, everything else 644
find "$APP_DIR" -type f -name "*.sh" -exec chmod 755 {} \;
find "$APP_DIR" -type f ! -name "*.sh" -exec chmod 644 {} \;
find "$APP_DIR" -type d -exec chmod 755 {} \;

# fix prefs file perms
PREFS_FILE="$APP_DIR/config/user_prefs.json"
if [ -f "$PREFS_FILE" ]; then
  chgrp www-data "$PREFS_FILE"
  chmod 660 "$PREFS_FILE"
fi

echo "🔁 Restarting service..."
systemctl restart gasera.service

echo "✅ Update complete."
echo "   If you encounter issues, try 'sudo systemctl status gasera.service' and 'sudo journalctl -u gasera.service'."