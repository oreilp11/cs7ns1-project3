# src/protocol/bob2_protocol.py

import struct
import socket
import zlib
import time


class Bob2Protocol:
    def __init__(self, version_major=0, version_minor=2):
        self.version_major = version_major
        self.version_minor = version_minor

    def build_message(self, message_type, dest_ipv4, dest_port, source_ipv4, source_port, sequence_number, message_content):
        # Create the header using Bob2Headers
        header = Bob2Headers(
            version_major=self.version_major,
            version_minor=self.version_minor,
            message_type=message_type,
            dest_ipv4=dest_ipv4,
            dest_port=dest_port,
            source_ipv4=source_ipv4,
            source_port=source_port,
            sequence_number=sequence_number
        ).build_header()

        # Calculate checksum
        checksum = zlib.crc32(message_content.encode('utf-8'))
        checksum_bytes = struct.pack('!I', checksum)

        # Build the full message
        message_length = len(message_content)
        length_bytes = message_length.to_bytes(5, byteorder='big')

        full_message = header + length_bytes + checksum_bytes + message_content.encode('utf-8')
        return full_message

    def parse_message(self, raw_data):
        # Parse the header
        header_data = raw_data[:23]  # Header size is 47 bytes
        header_info = Bob2Headers().parse_header(header_data)

        # Parse the rest of the message
        message_length = int.from_bytes(raw_data[23:28], byteorder='big')
        expected_checksum = struct.unpack('!I', raw_data[28:32])[0]
        message_content = raw_data[32:32 + message_length]
        actual_checksum = zlib.crc32(message_content)

        if expected_checksum != actual_checksum:
            raise ValueError("Checksum verification failed")

        # Add parsed message content to the header info
        header_info.update({
            "message_length": message_length,
            "checksum": expected_checksum,
            "message_content": message_content.decode('utf-8'),
        })

        return header_info


class Bob2Headers:
    def __init__(
            self, version_major=0, version_minor=2, message_type=0,
            dest_ipv4="localhost", dest_port=31000, source_ipv4="localhost", source_port=3000,
            sequence_number=0, timestamp=None
        ):
        self.version_major = version_major
        self.version_minor = version_minor
        self.message_type = message_type
        self.dest_ipv4 = dest_ipv4
        self.dest_port = dest_port
        self.source_ipv4 = source_ipv4
        self.source_port = source_port
        self.sequence_number = sequence_number
        self.timestamp = timestamp if timestamp is not None else int(
            time.time())

    def build_header(self):
        try:
            dest_ip_bytes = socket.inet_pton(socket.AF_INET, self.dest_ipv4)
            source_ip_bytes = socket.inet_pton(
                socket.AF_INET, self.source_ipv4)
        except socket.error:
            raise ValueError("Invalid IPv4 address")

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
        dest_ipv4 = socket.inet_ntop(socket.AF_INET, raw_data[3:7])
        dest_port = struct.unpack("!H", raw_data[7:9])[0]
        source_ipv4 = socket.inet_ntop(socket.AF_INET, raw_data[9:13])
        source_port = struct.unpack("!H", raw_data[13:15])[0]
        sequence_number = struct.unpack("!I", raw_data[15:19])[0]
        timestamp = struct.unpack("!I", raw_data[19:23])[0]

        return {
            "version_major": version_major,
            "version_minor": version_minor,
            "message_type": message_type,
            "dest_ipv4": dest_ipv4,
            "dest_port": dest_port,
            "source_ipv4": source_ipv4,
            "source_port": source_port,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        }