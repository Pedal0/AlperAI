"""
Trouve un port libre à partir d'un port de départ.
"""
import socket

def find_free_port(start_port=3000, max_attempts=100):
    port = start_port
    for _ in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                port += 1
    return None
