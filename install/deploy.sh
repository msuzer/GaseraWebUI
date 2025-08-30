#!/bin/bash
set -e

# --- Settings ---
IFACE="end0"
LAN_CIDR="192.168.0.1/24"
LAN_NET="192.168.0.0"
LAN_MASK="255.255.255.0"
LAN_GW="192.168.0.1"
LEASE_IP="192.168.0.100"   # the only IP to hand out
DNS1="8.8.8.8"

REPO_URL="https://github.com/msuzer/GaseraWebUI.git"
APP_DIR="/opt/GaseraWebUI"

echo "[1/9] Installing required packages..."
apt update
apt install -y isc-dhcp-server nginx python3 gpiod python3-pip python3-flask python3-waitress python3-netifaces python3-libgpiod python3-psutil git network-manager hostapd dnsmasq curl net-tools socat

echo "[2/9] Ensuring 'dnsmasq' won't conflict with isc-dhcp-server..."
# If dnsmasq is present, stop it so ISC DHCP can bind to ${IFACE}
systemctl disable --now dnsmasq 2>/dev/null || true

echo "[3/9] Setting file and folder permissions..."
mkdir -p "$APP_DIR" || true
chown -R www-data:www-data "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} \; || true
find "$APP_DIR" -type f -exec chmod 644 {} \; || true

echo "[4/9] Installing systemd service..."
cp gasera.service /etc/systemd/system/gasera.service
systemctl daemon-reexec
systemctl enable gasera.service
systemctl restart gasera.service

echo "[5/9] Installing Nginx config..."
cp gasera.conf /etc/nginx/sites-available/gasera.conf
ln -sf /etc/nginx/sites-available/gasera.conf /etc/nginx/sites-enabled/gasera.conf
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "[6/9] Setting GPIO permissions..."
cp 99-gpio.rules /etc/udev/rules.d/99-gpio.rules
groupadd -f gpio
usermod -aG gpio www-data
udevadm control --reload-rules
udevadm trigger
chown root:gpio /dev/gpiochip* 2>/dev/null || true
chmod 660 /dev/gpiochip* 2>/dev/null || true

# Create/replace the LAN connection used for DHCP gateway
if nmcli -t -f NAME con show | grep -qx "gasera-dhcp"; then
  nmcli con mod gasera-dhcp ipv4.method manual ipv4.addresses "${LAN_CIDR}"
  nmcli con mod gasera-dhcp connection.interface-name "${IFACE}"
else
  nmcli con add type ethernet ifname "${IFACE}" con-name gasera-dhcp ipv4.method manual ipv4.addresses "${LAN_CIDR}"
fi
nmcli con up gasera-dhcp

echo "[8/9] Configure ISC DHCP server to give ${LEASE_IP} on ${IFACE}..."
# Bind isc-dhcp-server to our interface
if grep -q '^INTERFACESv4=' /etc/default/isc-dhcp-server 2>/dev/null; then
  sed -i 's/^INTERFACESv4=.*/INTERFACESv4="'"${IFACE}"'"/' /etc/default/isc-dhcp-server
else
  echo 'INTERFACESv4="'"${IFACE}"'"' >> /etc/default/isc-dhcp-server
fi

# Create a minimal authoritative dhcpd.conf (single-IP pool)
DHCP_CONF="/etc/dhcp/dhcpd.conf"
cp -a "${DHCP_CONF}" "${DHCP_CONF}.bak.$(date +%s)" 2>/dev/null || true
cat > "${DHCP_CONF}" <<EOF
default-lease-time 600;
max-lease-time 7200;
authoritative;

subnet ${LAN_NET} netmask ${LAN_MASK} {
  range ${LEASE_IP} ${LEASE_IP};
  option routers ${LAN_GW};
  option domain-name-servers ${DNS1};
}
EOF

systemctl enable isc-dhcp-server
systemctl restart isc-dhcp-server

echo "[9/9] Final checks..."
systemctl --no-pager --full status isc-dhcp-server || true
ip addr show dev "${IFACE}" || true
echo "✅ Deployment complete. Plug Gasera in and it should get ${LEASE_IP}."
echo "   You can test with: echo -e '\x02 ASTS K0 \x03' | nc ${LEASE_IP} 8888"
echo "   You can re-run this script to fix any issues."