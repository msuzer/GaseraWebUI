#!/bin/bash
set -e

IFACE="end0"
DHCP_CONF="/etc/dhcp/dhcpd.conf"

echo "[1/7] Stopping and disabling app service..."
systemctl stop gasera.service 2>/dev/null || true
systemctl disable gasera.service 2>/dev/null || true
rm -f /etc/systemd/system/gasera.service
systemctl daemon-reexec

echo "[2/7] Removing Flask app from /opt..."
rm -rf /opt/GaseraWebUI

echo "[3/7] Removing Nginx configuration..."
rm -f /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-available/gasera.conf
systemctl restart nginx || true

echo "[4/7] Removing GPIO udev rule & restoring permissions..."
rm -f /etc/udev/rules.d/99-gpio.rules
udevadm control --reload-rules
udevadm trigger
for dev in /dev/gpiochip*; do
  [ -e "$dev" ] && chmod 600 "$dev" && chown root:root "$dev"
done

echo "[5/7] Remove DHCP LAN connection and restore previous NM state..."
if nmcli -t -f NAME con show | grep -qx "gasera-dhcp"; then
  nmcli con down gasera-dhcp || true
  nmcli con delete gasera-dhcp || true
  echo "Removed gasera-dhcp connection."
fi

echo "[6/7] Disable isc-dhcp-server and revert interface binding..."
systemctl disable --now isc-dhcp-server 2>/dev/null || true
# Comment out interface binding line to avoid surprises later
if [ -f /etc/default/isc-dhcp-server ]; then
  sed -i 's/^INTERFACESv4=.*/# INTERFACESv4=""/' /etc/default/isc-dhcp-server
fi
# Keep dhcpd.conf backup if we created one; do not delete packages

echo "[7/7] Done."
echo "🧽 Uninstallation complete. System is clean for a fresh deploy."
echo "   You can re-run deploy.sh to reinstall the app."