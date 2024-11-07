import csv
import socket
import random
import time
import threading
from bob2_protocol import Bob2Protocol

class Satellite:
    def __init__(self, sat_id):
        self.protocol = Bob2Protocol()
        # Load connected devices from the CSV file
        self.sat_host, self.satellites = self.load_network(sat_id)
        self.name = f"Satellite {sat_id}"
        if self.satellites:
            closest_satellite = self.satellites[0]
            self.next_sat_host = closest_satellite['ip']
            self.next_sat_port = closest_satellite['port']
        else:
            print("No satellites available")

        # Setup UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.sat_host)
        print(f"Satellite listening on {self.sat_host}")
        print(f"Closest Satellite: {self.next_sat_host}:{self.next_sat_port}")

    def load_network(self, id):
        act_sat = ()
        satellites = []
        with open('distances_common.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Device1'] == 'Satellite ' + str(id):
                    satellites.append({
                        'distance': float(row['Distance_km']),
                        'name': row['Device2'],
                        'ip': row['IP2'],
                        'port': int(row['Port2'])
                    })
                    act_sat = (row['IP1'], int(row['Port1']))
                elif row['Device2'] == 'Satellite ' + str(id):
                    satellites.append({
                        'distance': float(row['Distance_km']),
                        'name': row['Device1'],
                        'ip': row['IP1'],
                        'port': int(row['Port1'])
                    })
                    act_sat = (row['IP2'], int(row['Port2']))

        satellites.sort(key=lambda x: x['distance'])
        return act_sat, satellites

    def simulate_starlink_delay(self):
        """Simulate StarLink transmission delay with jitter"""
        base_delay = random.uniform(40, 60)  # Base delay 40-60ms
        jitter = random.uniform(2, 8)        # Additional jitter 2-8ms
        return (base_delay + jitter) / 1000  # Convert to seconds

    def forward_message(self, parsed_message):
        """Forward message to Ground Station or next satellite"""
        time.sleep(self.simulate_starlink_delay())
        success = False

        # Attempt to send to Ground Station first
        for device in self.satellites:
            if device['name'] == 'Ground Station':
                try:
                    message = self.protocol.build_message(
                        message_type=parsed_message["message_type"],
                        dest_ipv6="::1",  # Use dummy IPv6
                        dest_port=device['port'],
                        message_content=parsed_message["message_content"]
                    )
                    self.sock.sendto(message, (device['ip'], device['port']))
                    print(f"Forwarded message to Ground Station at {device['ip']}:{device['port']}")
                    success = True
                    break
                except Exception as e:
                    print(f"Error forwarding to Ground Station: {e}")
                    continue

        if not success:
            # If Ground Station is unreachable, forward to the next closest satellite
            for device in self.satellites:
                if 'Satellite' in device['name'] and device['name'] != self.name:
                    try:
                        message = self.protocol.build_message(
                            message_type=parsed_message["message_type"],
                            dest_ipv6='::1',  # Use dummy IPv6
                            dest_port=device['port'],
                            message_content=parsed_message["message_content"]
                        )
                        self.sock.sendto(message, (device['ip'], device['port']))
                        print(f"Forwarded message to {device['name']} at {device['ip']}:{device['port']}")
                        success = True
                        break
                    except Exception as e:
                        print(f"Error forwarding to {device['name']}: {e}")
                        continue

        if not success:
            print("No available devices to forward the message.")

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

                        # Send acknowledgment back to the sender immediately
                        try:
                            ack_message = self.protocol.build_message(
                                message_type=2,  # ACK message type
                                dest_ipv6="::1",
                                dest_port=addr[1],
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

    # Usage: python satellite.py <Satellite Name> <Listen IP> <Listen Port>
    if len(sys.argv) != 2:
        print("Usage: python satellite.py <Satellite id>")
        sys.exit(1)

    sat_id = sys.argv[1]

    satellite = Satellite(sat_id)
    satellite.start_relay()