import struct

import pytest

from utils import FIELD_NAMES, format_seconds_to_human_readable, parse_packet


# --- Helpers to build fake MNDP packets --------------------------------------
def field(field_type: int, value: bytes) -> bytes:
    """One TLV field: 2-byte type, 2-byte length (big-endian), then the value."""
    return struct.pack(">HH", field_type, len(value)) + value


def packet(*fields: bytes) -> bytes:
    """A full MNDP packet: 4-byte header followed by the fields."""
    return b"\x00\x00\x00\x00" + b"".join(fields)


# --- Fake test data----------------------------------
# MAC 02:00:00:00:00:01 is a "locally administered" address: not a real device.
# 192.0.2.0/24 and 2001:db8::/32 are IP ranges reserved for documentation.
ROUTER = packet(
    field(1, bytes.fromhex("020000000001")),                  # MAC
    field(5, b"TestRouter-1"),                                # identity
    field(7, b"7.23 (stable) 2026-05-25 09:05:50"),           # version
    field(8, b"MikroTik"),                                    # platform
    field(10, b"\x77\xa8\x45\x00"),                           # uptime, real byte order
    field(12, b"RBD52G-5HacD2HnD"),                           # board
    field(15, bytes.fromhex("20010db8000000000000000000000001")),  # 2001:db8::1
    field(15, bytes.fromhex("fe800000000000000000000000000001")),  # fe80::1
    field(16, b"bridge/ether1"),                              # interface
    field(17, bytes([192, 0, 2, 1])),                         # 192.0.2.1
    field(18, b"\x00"),                                       # unknown type
)

OWN_REQUEST = b"\x00\x00\x00\x00"


# --- Parser tests -------------------------------------------------------------
@pytest.mark.parametrize(
    "key, expected",
    [
        ("mac", "02:00:00:00:00:01"),
        ("identity", "TestRouter-1"),
        ("version", "7.23 (stable) 2026-05-25 09:05:50"),
        ("board", "RBD52G-5HacD2HnD"),
        ("interface", "bridge/ether1"),
        ("ipv4", "192.0.2.1"),
    ],
)
def test_decodes_fields(key, expected):
    assert parse_packet(ROUTER)[key] == expected


def test_uptime_is_little_endian():
    # These 4 bytes came from a real router: 4565111 seconds (~52 days).
    # Read as big-endian they'd be ~63 years, so this proves the byte order.
    assert parse_packet(ROUTER)["uptime"] == 4565111


def test_collects_all_ipv6_addresses():
    assert parse_packet(ROUTER)["ipv6"] == ["2001:db8::1", "fe80::1"]


def test_unknown_field_types_are_skipped():
    result = parse_packet(ROUTER)
    assert set(result) <= set(FIELD_NAMES.values())


def test_own_request_is_not_a_router():
    assert "mac" not in parse_packet(OWN_REQUEST)


# --- Formatting tests ---------------------------------------------------------
@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0s"),
        (59, "59s"),
        (3600, "1h"),
        (90061, "1d 1h 1m 1s"),
    ],
)
def test_format_seconds(seconds, expected):
    assert format_seconds_to_human_readable(seconds) == expected