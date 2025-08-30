#!/bin/bash
set -euo pipefail

# --- Settings ---
IFACE="end0"
LAN_ADDR="192.168.0.1/24"
LAN_NET="192.168.0.0"
LAN_MASK="255.255.255.0"
GATEWAY_IP="192.168.0.1"
LEASE_IP="192.168.0.100"
DNS1="8.8.8.8"

REPO_URL="https://github.com/msuzer/GaseraWebUI.git"
APP_DIR="/opt/GaseraWebUI"

echo "[1/10] Update & install packages..."
apt update
apt install -y isc-dhcp-server nginx python3 gpiod python3-pip python3-flask python3-waitress \
               python3-netifaces python3-libgpiod python3-psutil git network-manager hostapd \
               dnsmasq curl net-tools socat dos2unix

echo "[2/10] Avoid DHCP conflicts: disable dnsmasq..."
systemctl disable --now dnsmasq 2>/dev/null || true

echo "[3/10] App directory & permissions..."
mkdir -p "$APP_DIR"
chown -R www-data:www-data "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \; || true
find "$APP_DIR" -type f -exec chmod 644 {} \; || true

echo "[4/10] Install systemd service for app..."
cp gasera.service /etc/systemd/system/gasera.service
systemctl daemon-reexec
systemctl enable gasera.service
systemctl restart gasera.service

echo "[5/10] Install Nginx config..."
cp gasera.conf /etc/nginx/sites-available/gasera.conf
ln -sf /etc/nginx/sites-available/gasera.conf /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "[6/10] GPIO udev + permissions..."
cp 99-gpio.rules /etc/udev/rules.d/99-gpio.rules
groupadd -f gpio
usermod -aG gpio www-data
udevadm control --reload-rules
udevadm trigger
chown root:gpio /dev/gpiochip* 2>/dev/null || true
chmod 660 /dev/gpiochip* 2>/dev/null || true

echo "[7/10] NetworkManager: set ${IFACE} to ${LAN_ADDR} (gasera-dhcp)..."
if nmcli -t -f NAME con show | grep -qx "gasera-dhcp"; then
  nmcli con mod gasera-dhcp connection.interface-name "${IFACE}" ipv4.method manual ipv4.addresses "${LAN_ADDR}"
else
  nmcli con add type ethernet ifname "${IFACE}" con-name gasera-dhcp ipv4.method manual ipv4.addresses "${LAN_ADDR}"
fi
nmcli con up gasera-dhcp

echo "[8/10] Configure ISC DHCP (bind to ${IFACE}, lease ${LEASE_IP})..."
# Bind to interface
if grep -q '^INTERFACESv4=' /etc/default/isc-dhcp-server 2>/dev/null; then
  sed -i 's/^INTERFACESv4=.*/INTERFACESv4="'"${IFACE}"'"/' /etc/default/isc-dhcp-server
else
  echo 'INTERFACESv4="'"${IFACE}"'"' >> /etc/default/isc-dhcp-server
fi

# dhcpd.conf
DHCP_CONF="/etc/dhcp/dhcpd.conf"
cp -a "${DHCP_CONF}" "${DHCP_CONF}.bak.$(date +%s)" 2>/dev/null || true
cat > "${DHCP_CONF}" <<EOF
default-lease-time 600;
max-lease-time 7200;
authoritative;

subnet ${LAN_NET} netmask ${LAN_MASK} {
  range ${LEASE_IP} ${LEASE_IP};
  option routers ${GATEWAY_IP};
  option domain-name-servers ${DNS1};
}
EOF

# leases file sanity
touch /var/lib/dhcp/dhcpd.leases
chown dhcpd:dhcpd /var/lib/dhcp/dhcpd.leases 2>/dev/null || chown _dhcp:_dhcp /var/lib/dhcp/dhcpd.leases 2>/dev/null || true
chmod 644 /var/lib/dhcp/dhcpd.leases

echo "[9/10] Ensure DHCP starts after the NIC has its IPv4..."
# Wait-online helper
systemctl enable --now NetworkManager-wait-online.service || true

# systemd override to wait for IP on ${IFACE}
OVR_DIR="/etc/systemd/system/isc-dhcp-server.service.d"
mkdir -p "${OVR_DIR}"
cat > "${OVR_DIR}/override.conf" <<'EOF'
[Unit]
After=network-online.target NetworkManager.service
Wants=network-online.target

[Service]
ExecStartPre=/bin/sh -c 'until ip -4 addr show dev end0 | grep -q "inet 192.168.0.1/"; do sleep 1; done'
EOF

systemctl daemon-reload
systemctl enable isc-dhcp-server
systemctl restart isc-dhcp-server

echo "[10/10] Final checks..."
systemctl --no-pager --full status isc-dhcp-server || true
ss -lunp | grep ':67' || true
ip addr show dev "${IFACE}" || true

echo "✅ Deploy complete. Gasera should receive ${LEASE_IP} on ${IFACE}. Access its service at http://${LEASE_IP}:8888/"
echo "   You can test with: echo -e '\x02 ASTS K0 \x03' | nc ${LEASE_IP} 8888"
echo "   You can re-run this script to fix any issues."