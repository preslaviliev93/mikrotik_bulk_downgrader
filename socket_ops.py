import socket
import time
import utils

MNDP_PORT = 5678 # MikroTik Neighbor Discovery Protocol port
BROADCAST_ADDR = "255.255.255.255"
MNDP_REQUEST = b"\x00\x00\x00\x00" # MNDP request packet (4 bytes of zeros)


class SocketOPS:
    def __init__(self, ip_addr: str = BROADCAST_ADDR, port: int = MNDP_PORT):
        self.ip = ip_addr
        self.port = port
        self.sock = self.create_socket()

    def create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.port))
        sock.settimeout(1.0)
        return sock


    def receive(self, duration: float = 5.0) -> list[tuple[bytes, str]]:
        packets = []
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            try:
                data, (sender_ip, _sender_port) = self.sock.recvfrom(1500)
            except TimeoutError:
                continue
            packets.append((data, sender_ip))
        return packets


    def send_request(self) -> int:
        return self.sock.sendto(MNDP_REQUEST, (self.ip, self.port) )



    def close_sock(self) -> None:
        self.sock.close()


    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close_sock()





def discover(duration: float = 5.0) -> dict[str, dict]:
    with SocketOPS() as s:
        s.send_request()
        results = {}
        for data, sender in s.receive(duration):
            parsed_data = utils.parse_packet(data)
            if "mac" not in parsed_data:
                continue
            results[parsed_data["mac"]] = parsed_data
        return results



if __name__ == "__main__":

    discovered = discover(duration=5.0)
    for mac, info in discovered.items():
        uptime_seconds = info.get("uptime")
        if uptime_seconds is not None:
            uptime_human_readable = utils.format_seconds_to_human_readable(uptime_seconds)
        else:
            uptime_human_readable = 'N/A'
        print(f"MAC: {mac}, IP: {info.get('ipv4', 'N/A')}, Identity: {info.get('identity', 'N/A')}, Version: {info.get('version', 'N/A')}, Uptime: {uptime_human_readable}")