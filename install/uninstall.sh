#!/bin/bash

set -e

echo "[1/6] Stopping and disabling systemd service..."
systemctl stop gasera.service || true
systemctl disable gasera.service || true
rm -f /etc/systemd/system/gasera.service
systemctl daemon-reexec

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

echo "[5/6] Removing Python packages..."
pip3 uninstall -y waitress flask psutil || true

echo "[6/6] Final cleanup of GPIO permissions..."
for dev in /dev/gpiochip*; do
    [ -e "$dev" ] && chmod 600 "$dev" && chown root:root "$dev"
done

echo "🧽 Uninstallation complete. You can now redeploy with a clean slate."
