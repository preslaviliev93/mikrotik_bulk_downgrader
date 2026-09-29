import ipaddress
import struct

FIELD_NAMES = {
    1: "mac",
    5: "identity",
    7: "version",
    8: "platform",
    10: "uptime",
    11: "software_id",
    12: "board",
    15: "ipv6",
    16: "interface",
    17: "ipv4",
}


def split_fields(data: bytes) -> list[tuple[int, bytes]]:
    """Cut an MNDP packet into (type, value) pairs."""
    fields = []
    offset = 4                                   
    while offset + 4 <= len(data):               
        field_type, length = struct.unpack_from(">HH", data, offset)
        offset += 4
        value = data[offset:offset + length]
        if len(value) < length:                  
            break
        fields.append((field_type, value))
        offset += length
    return fields


def decode_value(field_type: int, value: bytes):
    """Turn one field's raw bytes into a readable value."""
    if field_type == 1:                          # MAC address
        return ":".join(f"{b:02x}" for b in value)
    if field_type == 10:                         # uptime
        return int.from_bytes(value, "little")
    if field_type == 15:                         # IPv6
        return str(ipaddress.IPv6Address(value))
    if field_type == 17:                         # IPv4
        return str(ipaddress.IPv4Address(value))
    return value.decode("utf-8", errors="replace")   # text fields


def parse_packet(data: bytes) -> dict:
    """Parse a whole packet into a dict of readable values."""
    result = {"ipv6": []}
    for field_type, value in split_fields(data):
        name = FIELD_NAMES.get(field_type)
        if name is None:                         # unknown type
            continue
        decoded = decode_value(field_type, value)
        if name == "ipv6":                       
            result["ipv6"].append(decoded)
        else:
            result[name] = decoded
    return result





def format_neighbor(decoded_data: dict) -> str:
    LABELS = {
    "identity": "Identity",
    "mac": "MAC Address",
    "ipv4": "IPv4 Address",
    "board": "Board",
    "version": "Version",
    "uptime": "Uptime",
}
    
    lines = []
    for key, label in LABELS.items():
        value = decoded_data.get(key, "-")
        lines.append(f"{label:<13}: {value}")
    return "\n".join(lines)


def format_seconds_to_human_readable(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)