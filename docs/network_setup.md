# OPiZ3 Network Configuration

## 📶 Connect to Wi-Fi Access Points

Replace SSID and password strings with your actual Wi-Fi credentials:

```bash
nmcli dev wifi list
nmcli device wifi connect "SSID1" password "password1" name "preferred_ap"
nmcli device wifi connect "SSID2" password "password2" name "secondary_ap"
```

To connect to open networks (no password):

```bash
nmcli device wifi connect "SSID3" name "open_ap"
```

Optional TUI interface:

```bash
nmtui
```

Set autoconnect preferences:

```bash
nmcli connection modify preferred_ap connection.autoconnect yes
nmcli connection modify secondary_ap connection.autoconnect yes
nmcli connection modify preferred_ap connection.autoconnect-priority 100
nmcli connection modify secondary_ap connection.autoconnect-priority 50
```

Check status:

```bash
nmcli device status
ip a show wlan0
```

---

## 🌐 Configure Static IP on Ethernet (for Gasera)

Assign static IP to `eth0`:

```bash
sudo ip addr add 192.168.100.1/24 dev eth0
sudo ip link set eth0 up
```

Or using NetworkManager:

```bash
nmcli con add type ethernet ifname eth0 con-name gasera-static ip4 192.168.100.1/24
nmcli con up gasera-static
```

---

## 🧪 Test Gasera Communication

Check reachability:

```bash
ping 192.168.100.10
```

Install `netcat` for manual testing:

```bash
sudo apt install netcat

# Send sample ASTS request
echo -e '\x02 ASTS K0 \x03' | nc 192.168.100.10 8888
```

Alternatively, use the Python test script:

```bash
python3 test_gasera.py
```

