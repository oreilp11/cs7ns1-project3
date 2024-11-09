# headers/bob2_headers.py

import struct
import socket
import time


class BobbHeaders:
    def __init__(self, version_major=0, version_minor=0, message_type=0,
                 dest_ipv6="::1", dest_port=12345, source_ipv6="::1", source_port=12345,
                 sequence_number=0, timestamp=None):
        self.version_major = version_major
        self.version_minor = version_minor
        self.message_type = message_type
        self.dest_ipv6 = dest_ipv6
        self.dest_port = dest_port
        self.source_ipv6 = source_ipv6
        self.source_port = source_port
        self.sequence_number = sequence_number
        self.timestamp = timestamp if timestamp is not None else int(
            time.time())

    def build_header(self):
        try:
            dest_ip_bytes = socket.inet_pton(socket.AF_INET6, self.dest_ipv6)
            source_ip_bytes = socket.inet_pton(
                socket.AF_INET6, self.source_ipv6)
        except socket.error:
            raise ValueError("Invalid IPv6 address")

        header = struct.pack("!BBB", self.version_major,
                             self.version_minor, self.message_type)
        header += dest_ip_bytes + struct.pack("!H", self.dest_port)
        header += source_ip_bytes + struct.pack("!H", self.source_port)
        header += struct.pack("!I", self.sequence_number)
        header += struct.pack("!I", self.timestamp)

        return header

    def parse_header(self, raw_data):
        version_major, version_minor, message_type = struct.unpack(
            "!BBB", raw_data[:3])
        dest_ipv6 = socket.inet_ntop(socket.AF_INET6, raw_data[3:19])
        dest_port = struct.unpack("!H", raw_data[19:21])[0]
        source_ipv6 = socket.inet_ntop(socket.AF_INET6, raw_data[21:37])
        source_port = struct.unpack("!H", raw_data[37:39])[0]
        sequence_number = struct.unpack("!I", raw_data[39:43])[0]
        timestamp = struct.unpack("!I", raw_data[43:47])[0]

        return {
            "version_major": version_major,
            "version_minor": version_minor,
            "message_type": message_type,
            "dest_ipv6": dest_ipv6,
            "dest_port": dest_port,
            "source_ipv6": source_ipv6,
            "source_port": source_port,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        }

    
# protocol/optional_headers.py

class BobbOptionalHeaders:
    def __init__(self, timestamp=None, hop_count=255, priority=0, encryption_algo="None"):
        self.timestamp = timestamp if timestamp else int(time.time())
        self.hop_count = hop_count
        self.priority = priority
        self.encryption_algo = encryption_algo

    def build_optional_header(self):
        header = struct.pack("!I", self.timestamp)  # 4 bytes for timestamp
        header += struct.pack("!B", self.hop_count)  # 1 byte for hop count
        header += struct.pack("!B", self.priority)  # 1 byte for priority
        # 16 bytes for encryption_algo
        header += self.encryption_algo.encode('utf-8').ljust(16, b'\0')
        return header

    def parse_optional_header(self, raw_data):
        timestamp = struct.unpack("!I", raw_data[:4])[0]
        hop_count = struct.unpack("!B", raw_data[4:5])[0]
        priority = struct.unpack("!B", raw_data[5:6])[0]
        encryption_algo = raw_data[6:22].decode('utf-8').rstrip('\0')
        return {
            "timestamp": timestamp,
            "hop_count": hop_count,
            "priority": priority,
            "encryption_algo": encryption_algo
        }

