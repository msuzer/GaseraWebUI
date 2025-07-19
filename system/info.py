import platform
IS_LINUX = platform.system() == "Linux"

if IS_LINUX:

    import psutil
    import platform
    import time
    import os
    import netifaces

    def get_ip_mac(interface="wlan0"):
        try:
            ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
            mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
            return ip, mac
        except Exception:
            return "N/A", "N/A"

    def get_system_info():
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load1, load5, load15 = os.getloadavg()
        ip, mac = get_ip_mac("wlan0")

        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": mem.percent,
            "memory_used": round(mem.used / (1024**2), 1),
            "memory_total": round(mem.total / (1024**2), 1),
            "disk_percent": disk.percent,
            "disk_used": round(disk.used / (1024**3), 2),
            "disk_total": round(disk.total / (1024**3), 2),
            "load_avg": [round(load1, 2), round(load5, 2), round(load15, 2)],
            "uptime": int(time.time() - psutil.boot_time()),
            "platform": platform.platform(),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "ip_address": ip,
            "mac_address": mac
        }
else:
    from .info_dummy import get_system_info, get_ip_mac