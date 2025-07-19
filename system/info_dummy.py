import platform
import random
import time

print("info_dummy.py running in dummy mode (non-Linux platform)")

def get_ip_mac(interface="dummy0"):
    print(f"[DUMMY] get_ip_mac({interface})")
    return "127.0.0.1", "00:00:00:00:00:00"

def get_system_info():
    print("[DUMMY] get_system_info()")
    
    cpu_percent = round(random.uniform(5, 50), 1)         # simulate 5–50% CPU
    memory_percent = round(random.uniform(30, 80), 1)     # simulate 30–80% RAM usage
    memory_total = 4096.0                                 # pretend 4 GB system
    memory_used = round(memory_total * memory_percent / 100, 1)

    disk_total = 64.0                                     # pretend 64 GB storage
    disk_percent = round(random.uniform(20, 70), 1)
    disk_used = round(disk_total * disk_percent / 100, 2)

    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "memory_used": memory_used,
        "memory_total": memory_total,
        "disk_percent": disk_percent,
        "disk_used": disk_used,
        "disk_total": disk_total,
        "load_avg": [0.0, 0.0, 0.0],
        "uptime": int(time.time() - 3600),  # simulate 1-hour uptime
        "platform": platform.platform(),
        "cpu_cores": 4,
        "cpu_threads": 8,
        "ip_address": "127.0.0.1",
        "mac_address": "00:00:00:00:00:00"
    }
