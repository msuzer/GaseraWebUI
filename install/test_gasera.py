import socket
import time

HOST = '192.168.100.10'
PORT = 8888

query = "ASTS K0"
framed = b'\x02 ' + query.encode() + b' ' + b'\x03'

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(3)
    s.connect((HOST, PORT))
    time.sleep(0.2)
    s.sendall(framed)

    try:
        response = s.recv(1024)
        print("Received:", response)
        print("As text:", response.decode(errors='ignore'))
    except socket.timeout:
        print("No response received (timeout)")
