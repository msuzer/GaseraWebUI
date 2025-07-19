import socket
import threading
from typing import Optional, Callable

STX = chr(2)
ETX = chr(3)

class GaseraTCPClient:
    def __init__(self, host: str, port: int,
                 timeout: float = 2.0,
                 on_connection_change: Optional[Callable[[bool], None]] = None,
                 on_status_change: Optional[Callable[[object], None]] = None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.on_connection_change = on_connection_change
        self.on_status_change = on_status_change

        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._connected = False

    def connect(self) -> bool:
        with self._lock:
            self.disconnect()
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                self._sock.settimeout(self.timeout)
                self._connected = True
                if self.on_connection_change:
                    self.on_connection_change(True)
                return True
            except (socket.timeout, OSError):
                self._sock = None
                self._connected = False
                if self.on_connection_change:
                    self.on_connection_change(False)
                return False

    def disconnect(self):
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                finally:
                    self._sock = None
            if self._connected:
                self._connected = False
                if self.on_connection_change:
                    self.on_connection_change(False)

    def is_connected(self) -> bool:
        return self._connected

    def is_online(self, timeout=1.0):
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except Exception:
            return False

    def send_command(self, command: str) -> Optional[str]:
        with self._lock:
            if not self._sock:
                if not self.connect():
                    return None
            try:
                assert self._sock
                print(f"[TCP] Sending command: {command.strip()}")
                self._sock.sendall(command.encode("ascii"))
                response = self._recv_until_etx()
                if response is None:
                    print("[TCP] No response or timeout occurred")
                else:
                    print(f"[TCP] Response: {response.strip()}")
                return response
            except (socket.timeout, OSError) as e:
                print(f"[TCP] Communication error: {e}")
                self.disconnect()
                return None

    def _recv_until_etx(self) -> Optional[str]:
        assert self._sock
        self._sock.settimeout(self.timeout)  # Enforce timeout explicitly per call
        buffer = ""
        try:
            while True:
                chunk = self._sock.recv(1024)
                if not chunk:
                    print("[TCP] Disconnected or empty chunk")
                    break
                buffer += chunk.decode("ascii", errors="replace")
                if ETX in buffer:
                    break
        except socket.timeout:
            print("[TCP] Receive timeout — no ETX received")
            return None
        except OSError as e:
            print(f"[TCP] Socket error: {e}")
            return None

        start = buffer.find(STX)
        end = buffer.find(ETX)
        if start != -1 and end != -1:
            return buffer[start:end + 1]
        print("[TCP] Received partial or malformed data:", buffer)
        return buffer if buffer else None

# Initialize the TCP client with the configured IP and port
from .config import GASERA_IP_ADDRESS, GASERA_PORT_NUMBER
tcp_client = GaseraTCPClient(GASERA_IP_ADDRESS, GASERA_PORT_NUMBER)