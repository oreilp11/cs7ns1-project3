import csv
import socket
import os
import time

#from bob2_protocol import Bob2Protocol
from bob2_ipv4 import Bob2Protocol

class GroundStationNode:
    def __init__(self, device_list_path, connection_list_path):
        self.device_list_path = device_list_path
        self.connection_list_path = connection_list_path
        self.protocol = Bob2Protocol()
        self.name = "Ground Station"
        self.sat_host = self.load_network()

        # self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.sat_host)
        print(f"{self.name} listening on {self.sat_host}")


    def load_network(self):
        current_device = ()
        with open(self.device_list_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'] == self.name:
                    current_device = (row['ip'], int(row['port']))
        return current_device


    def accept_responses(self, verbose=False):
        """Start listening for and forwarding messages"""
        try:
            print("Waiting for incoming messages...")
            message_data, addr = self.sock.recvfrom(4096)
            print(f"Received message from {addr}")
            if verbose:
                print(f"DEBUG: Message length: {len(message_data)} bytes")
                print(f"DEBUG: Raw message received: {message_data[:100]}...")  # Print first 100 bytes

            try:
                parsed_message = self.protocol.parse_message(message_data)
                end_to_end_delay = time.time() - parsed_message['timestamp']
                print(f"End to End delay: {end_to_end_delay:0.4}s")

                if verbose:
                    print(f"DEBUG: Parsed message: {parsed_message}")
                if parsed_message["message_type"] == 2:
                    print(f"Received ACK from {addr}")
                    return

                # Send acknowledgment back to the sender immediately
                try:
                    # ack_message = self.protocol.build_message(
                    #     message_type=2,  # ACK message type
                    #     dest_ipv6="::1",
                    #     dest_port=addr[1],
                    #     source_ipv6="::1",
                    #     source_port=self.sat_host[1],
                    #     sequence_number=0,
                    #     message_content="ACK"
                    # )

                    ack_message = self.protocol.build_message(
                        message_type=2,  # ACK message type
                        dest_ipv4=addr[0],
                        dest_port=addr[1],
                        source_ipv4=self.sat_host[0],
                        source_port=self.sat_host[1],
                        sequence_number=0,
                        message_content="ACK"
                    )

                    self.sock.sendto(ack_message, addr)
                    if verbose:
                        print(f"DEBUG: Sent ACK to {addr}")
                except Exception as e:
                    print(f"Error sending ACK: {e}")
            except ValueError as e:
                print(f"Error parsing message: {e}")
        except Exception as e:
            print(f"Error in message handling: {e}")


if __name__ == "__main__":
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
    devices = os.path.join(base_path, "devices_ipv4.csv")
    connections = os.path.join(base_path, "distances_common.csv")

    satellite = GroundStationNode(devices, connections)
    input("Ground Station Online. Press any key to start...")
    
    try:
        while True:
            satellite.accept_responses(verbose=True)
    except KeyboardInterrupt:
        print("Simulation stopped by user")