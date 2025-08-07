#!/bin/bash

set -e

REPO_URL="https://github.com/msuzer/GaseraWebUI.git"
APP_DIR="/opt/GaseraWebUI"

echo "[1/9] Updating system..."
apt update && apt upgrade -y

echo "[2/9] Installing required packages..."
apt install -y nginx python3 python3-pip python3-flask python3-psutil git network-manager hostapd dnsmasq curl net-tools socat

echo "[3/9] Cloning Flask app..."
rm -rf "$APP_DIR"
git clone "$REPO_URL" "$APP_DIR"
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"

echo "[4/9] Installing Python dependencies..."
pip3 install waitress  # Add more if needed

echo "[5/9] Installing systemd service..."
cp gasera.service /etc/systemd/system/gasera.service
systemctl daemon-reexec
systemctl enable gasera.service
systemctl restart gasera.service

echo "[6/9] Installing Nginx config..."
cp gasera.conf /etc/nginx/sites-available/gasera.conf
ln -sf /etc/nginx/sites-available/gasera.conf /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "[7/9] Setting file and folder permissions..."
chown -R www-data:www-data /opt/GaseraWebUI
find /opt/GaseraWebUI -type d -exec chmod 755 {} \;
find /opt/GaseraWebUI -type f -exec chmod 644 {} \;

echo "[8/9] Setting GPIO permissions..."
cp 99-gpio.rules /etc/udev/rules.d/99-gpio.rules
groupadd -f gpio
usermod -aG gpio www-data
udevadm control --reload-rules
udevadm trigger

echo "[9/9] Adjusting GPIO device access..."
chown root:gpio /dev/gpiochip* || true
chmod 660 /dev/gpiochip* || true

echo "✅ Deployment complete!"
