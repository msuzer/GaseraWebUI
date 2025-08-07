# 🟠 Orange Pi Zero 3 – First Boot Setup via UART and Ethernet

This guide walks you through setting up your **Orange Pi Zero 3 (OPiZ3)** from scratch, using:
- a prepared `.img.xz` OS image. I used the image prepared by [stas2z](https://github.com/stas2z), found on [GitHub Link](https://github.com/stas2z/orange-pi-images/releases/download/0.2-bookworm/Orangepizero3_1.0.2_debian_bookworm_server_linux6.1.31.img.xz)
- UART serial connection for console access
- Ethernet for SSH login

---

## 📥 Step 1: Burn the OS Image to microSD

### 🔧 Requirements
- `.img.xz` image file (e.g., `orangepi_debian.img.xz`)
- SD card reader
- Debian-based Linux system

### 🧯 WARNING: This will erase the SD card.

### ✅ Steps

1. Insert the microSD card into your PC.
2. Identify the device name:

   ```bash
   lsblk
   ```

   Example: `/dev/sdb`, `/dev/sdX` or `/dev/mmcblk0` (not a partition like `/dev/sdX1`)

3. Decompress and Burn the image:

   Using correct path to image and sd-card path:

   ```bash
   xz -d /path/to/image.img.xz
   sudo dd if=/path/to/image.img of=/dev/sdb bs=8M status=progress conv=fsync
   ```

   Or do all at once:

   ```bash
   xz -dc /path/to/image.img.xz | sudo dd of=/dev/sdb bs=8M status=progress conv=fsync
   ```

4. Flush buffers and eject the card:

   ```bash
   sync
   sudo eject /dev/sdX
   ```

---

## 🔌 Step 2: Connect Hardware

### UART Wiring (3 Pins Only)
| OPiZ3 Pin | USB-UART Module |
|----------:|----------------:|
| TX        | RX              |
| RX        | TX              |
| GND       | GND             |

> 🛑 **Do not connect 5V or 3.3V pins** to avoid damaging the board.

### Additional Connections:
- Insert the microSD card into OPiZ3.
- Connect Ethernet cable to router or PC with DHCP.
- Plug in power to boot the board.

---

## 📡 Step 3: Serial Console Access with Minicom

1. Identify UART device:

   ```bash
   dmesg | grep ttyUSB
   ```

   (Usually `/dev/ttyUSB0`)

2. Start minicom:

   ```bash
   sudo minicom -D /dev/ttyUSB0 -b 115200
   ```

3. Wait for boot messages. You should see something like:

   ```
   U-Boot SPL ...
   orangepi login:
   ```

4. Login (default credentials may vary):

   | Username | Password   |
   |----------|------------|
   | `root`   | `orangepi` |
   | or       | (blank)    |

---

## 🌐 Step 4: Get IP Address and SSH In

Once logged in:

```bash
ip a
```

Find the line for `eth0` or `end0`:

```
inet 192.168.1.123/24 ...
```

Then on your Debian PC:

```bash
ssh root@192.168.1.123
```

> Replace `192.168.1.123` with the actual IP shown.

---

## 🛠️ (Optional) Enable SSH on Boot

SSH is usually enabled by default. If not, you can enable it:

```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

---

## ✅ Success!

You are now connected to your OPiZ3 via SSH over Ethernet. UART can now be disconnected if no longer needed.

---

## 📌 Tips

- Use `nmap` to scan your network for the OPiZ3 if you can't find the IP:

  ```bash
  sudo nmap -sn 192.168.1.0/24
  ```

- Save a minicom config for easier reuse:

  ```bash
  sudo minicom -s
  ```

---

## 🧪 Bonus: Verify SD Card Write (Optional)

```bash
sudo cmp <(xz -dc /path/to/image.img.xz) /dev/sdX
```

No output = successful write.

---

## 🔗 Resources

- [Orange Pi Official Website](https://www.orangepi.org/)
- [Debian Images for Orange Pi](https://wiki.debian.org/InstallingDebianOn/Allwinner)

---

MIT License. Documentation by [Mehmet H Suzer].
