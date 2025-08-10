#!/bin/bash
# Gasera Web UI uninstallation script

set -e

APP_DIR="/opt/GaseraWebUI"
LOG_FILE="/var/log/gasera-uninstall.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "🧹 Starting Gasera Web UI uninstallation..."

echo "[1/6] Stopping and disabling systemd services..."
systemctl stop gasera.service || true
systemctl disable gasera.service || true
rm -f /etc/systemd/system/gasera.service
systemctl stop gasera-ingest.service || true
systemctl disable gasera-ingest.service || true
rm -f /etc/systemd/system/gasera-ingest.service
systemctl daemon-reload

echo "[2/6] Removing Flask app from /opt..."
rm -rf /opt/GaseraWebUI

echo "[3/6] Removing Nginx configuration..."
rm -f /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-available/gasera.conf
systemctl restart nginx

echo "[4/6] Removing GPIO udev rule..."
rm -f /etc/udev/rules.d/99-gpio.rules
udevadm control --reload-rules
udevadm trigger

echo "[5/6] Take down and remove the static ethernet connection"
if nmcli con show | grep -q "gasera-static"; then
    nmcli con down gasera-static || true
    nmcli con delete gasera-static
    echo "Removed gasera-static connection."
fi

echo "[6/6] Final cleanup of GPIO permissions..."
for dev in /dev/gpiochip*; do
    [ -e "$dev" ] && chmod 600 "$dev" && chown root:root "$dev"
done
groupdel gpio || true

echo "🧽 Uninstallation complete."
echo "📄 Log saved to: $LOG_FILE"
echo "You can now redeploy with a clean slate."

