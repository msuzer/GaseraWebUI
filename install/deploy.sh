#!/bin/bash

set -e

REPO_URL="https://github.com/msuzer/GaseraWebUI.git"
APP_DIR="/opt/GaseraWebUI"

echo "[1/8] Updating system..."
apt update && apt upgrade -y

echo "[2/8] Installing required packages..."
apt install -y nginx python3 python3-pip python3-flask python3-psutil git network-manager hostapd dnsmasq curl net-tools socat

echo "[3/8] Installing Python dependencies..."
pip3 install waitress  # Add more if needed

echo "[4/8] Setting file and folder permissions..."
chown -R www-data:www-data "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \;
find "$APP_DIR" -type f -exec chmod 644 {} \;

echo "[5/8] Installing systemd service..."
cp gasera.service /etc/systemd/system/gasera.service
systemctl daemon-reexec
systemctl enable gasera.service
systemctl restart gasera.service

echo "[6/8] Installing Nginx config..."
cp gasera.conf /etc/nginx/sites-available/gasera.conf
ln -sf /etc/nginx/sites-available/gasera.conf /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "[7/8] Setting GPIO permissions..."
cp 99-gpio.rules /etc/udev/rules.d/99-gpio.rules
groupadd -f gpio
usermod -aG gpio www-data
udevadm control --reload-rules
udevadm trigger

echo "[8/8] Adjusting GPIO device access..."
chown root:gpio /dev/gpiochip* || true
chmod 660 /dev/gpiochip* || true

echo "✅ Deployment complete!"
