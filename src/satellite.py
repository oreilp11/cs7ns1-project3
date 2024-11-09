import csv
import socket
import random
import time
import os
import threading
from bob2_protocol import Bob2Protocol
from find_shortest_way import find_shortest_path

class Satellite:
    def __init__(self, sat_id):
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        self.protocol = Bob2Protocol()
        self.sat_id = int(sat_id)  # Ensure sat_id is an integer
        self.sat_host, self.next_device, self.shortest_path = self.load_network()
        self.name = f"Satellite {sat_id}"

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.sat_host)
        print(f"{self.name} listening on {self.sat_host}")
        print(f"Shortest path to Ground Station: {self.shortest_path}")
        print(f"Next device: {self.next_device}")

    def load_network(self):
        current_device = ()
        shortest_path = find_shortest_path(self.sat_id, -1)
        # ...existing code...
        with open(os.path.join(self.base_path, 'devices_ip.csv'), 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            devices = {}
            for row in reader:
                devices[int(row['id'])] = (row['ip'], int(row['port']))

            current_device = devices[self.sat_id]
            if len(shortest_path) > 1:
                next_device_id = shortest_path[1]
                next_device = devices[next_device_id]
            else:
                next_device = None

        return current_device, next_device, shortest_path

    def simulate_starlink_delay(self):
        """Simulate StarLink transmission delay with jitter"""
        base_delay = random.uniform(40, 60)  # Base delay 40-60ms
        jitter = random.uniform(2, 8)        # Additional jitter 2-8ms
        return (base_delay + jitter) / 1000  # Convert to seconds

    def forward_message(self, parsed_message):
        # Simulate delay
        time.sleep(self.simulate_starlink_delay())

        if self.next_device:
            try:
                message = self.protocol.build_message(
                    message_type=parsed_message["message_type"],
                    dest_ipv6="::1",
                    dest_port=self.next_device[1],
                    source_ipv6="::1",
                    source_port=self.sat_host[1],
                    sequence_number=0,
                    message_content=parsed_message["message_content"]
                )
                self.sock.sendto(message, self.next_device)
                print(f"Forwarded message to {self.next_device} along path {self.shortest_path}")
            except Exception as e:
                print(f"Error forwarding to next device: {e}")
        else:
            print("No next device to forward the message.")

    def start_relay(self):
        """Start listening for and forwarding messages"""
        try:
            while True:
                try:
                    print("Waiting for incoming messages...")
                    message_data, addr = self.sock.recvfrom(4096)
                    print(f"DEBUG: Raw message received: {message_data[:100]}...")  # Print first 100 bytes
                    print(f"DEBUG: Message length: {len(message_data)} bytes")
                    print(f"Received message from {addr}")


                    try:
                        parsed_message = self.protocol.parse_message(message_data)


                        print(f"DEBUG: Parsed message: {parsed_message}")
                        if parsed_message["message_type"] == 2:
                            print(f"Received ACK from {addr}")
                            continue

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

                        # Handle message forwarding in a separate thread
                        threading.Thread(target=self.forward_message, args=(parsed_message,)).start()
                    except ValueError as e:
                        print(f"Error parsing message: {e}")
                except Exception as e:
                    print(f"Error in message handling: {e}")
                    continue

        except KeyboardInterrupt:
            print(f"\n{self.name} relay stopped by user")
        finally:
            self.sock.close()

if __name__ == "__main__":
    import sys

    # Usage: python satellite.py <Satellite Name>
    if len(sys.argv) != 2:
        print("Usage: python satellite.py <Satellite id>")
        sys.exit(1)

    sat_id = sys.argv[1]

    satellite = Satellite(sat_id)
    satellite.start_relay()