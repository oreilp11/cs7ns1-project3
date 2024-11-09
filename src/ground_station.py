import csv
import socket
import os
from bob2_protocol import Bob2Protocol

class GroundStationNode:
    def __init__(self):
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        self.protocol = Bob2Protocol()
        self.name = "Ground Station"
        self.sat_host = self.load_network()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.sat_host)
        print(f"{self.name} listening on {self.sat_host}")

    def load_network(self):
        current_device = ()
        with open(os.path.join(self.base_path, 'devices_ip.csv'), 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'] == self.name:
                    current_device = (row['ip'], int(row['port']))
        return current_device


    def accept_responses(self):
        """Start listening for and forwarding messages"""
        try:
            print("Waiting for incoming messages...")
            message_data, addr = self.sock.recvfrom(4096)
            print(f"Received message from {addr}")
            print(f"DEBUG: Message length: {len(message_data)} bytes")
            print(f"DEBUG: Raw message received: {message_data[:100]}...")  # Print first 100 bytes

            try:
                parsed_message = self.protocol.parse_message(message_data)

                print(f"DEBUG: Parsed message: {parsed_message}")
                if parsed_message["message_type"] == 2:
                    print(f"Received ACK from {addr}")
                    return

                # Send acknowledgment back to the sender immediately
                try:
                    ack_message = self.protocol.build_message(
                        message_type=2,  # ACK message type
                        dest_ipv6="::1",
                        dest_port=addr[1],
                        source_ipv6="::1",
                        source_port=self.sat_host[1],
                        sequence_number=0,
                        message_content="ACK"
                    )
                    self.sock.sendto(ack_message, addr)
                    print(f"DEBUG: Sent ACK to {addr}")
                except Exception as e:
                    print(f"Error sending ACK: {e}")
            except ValueError as e:
                print(f"Error parsing message: {e}")
        except Exception as e:
            print(f"Error in message handling: {e}")

if __name__ == "__main__":
    satellite = GroundStationNode()
    try:
        while True:
            satellite.accept_responses()
    except KeyboardInterrupt:
        print("Simulation stopped by user")