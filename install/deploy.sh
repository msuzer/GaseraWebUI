#!/bin/bash
# Gasera Web UI deployment script

set -e

REPO_URL="https://github.com/msuzer/GaseraWebUI.git"
APP_DIR="/opt/GaseraWebUI"
LOG_FILE="/var/log/gasera-deploy.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "🚀 Starting Gasera Web UI deployment..."

echo "[1/8] Updating package lists and installing required packages..."
apt update
apt install -y nginx python3 gpiod python3-pip python3-flask python3-waitress \
               python3-netifaces python3-libgpiod python3-psutil python3-sqlalchemy \
               git network-manager hostapd dnsmasq curl net-tools socat

echo "[2/8] Setting file and folder permissions..."
chown -R www-data:www-data "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \;
find "$APP_DIR" -type f -exec chmod 644 {} \;

echo "[3/8] Installing services..."
cp gasera-ingest.service /etc/systemd/system/
cp gasera.service /etc/systemd/system/
systemctl daemon-reload

echo "[4/8] Enabling and starting services..."
# Start ingest service first
systemctl enable --now gasera-ingest
systemctl is-active --quiet gasera-ingest && echo "✅ gasera-ingest is running." || echo "❌ gasera-ingest failed to start."

# Then enable and restart gasera service
systemctl enable gasera.service
systemctl restart gasera.service
systemctl is-active --quiet gasera && echo "✅ gasera is running." || echo "❌ gasera failed to start."

echo "[5/8] Installing Nginx config..."
cp gasera.conf /etc/nginx/sites-available/gasera.conf
ln -sf /etc/nginx/sites-available/gasera.conf /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx
echo "✅ Nginx restarted with new configuration."

echo "[6/8] Setting GPIO permissions..."
cp 99-gpio.rules /etc/udev/rules.d/99-gpio.rules
groupadd -f gpio
usermod -aG gpio www-data
udevadm control --reload-rules
udevadm trigger

echo "[7/8] Adjusting GPIO device access..."
chown root:gpio /dev/gpiochip* || true
chmod 660 /dev/gpiochip* || true

echo "[8/8] Setting up static IP for Gasera..."
nmcli con add type ethernet ifname end0 con-name gasera-static ip4 192.168.100.1/24 || true
nmcli con up gasera-static || true

echo "🎉 Deployment complete!"
echo "📄 Log saved to: $LOG_FILE"