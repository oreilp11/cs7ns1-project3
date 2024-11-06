from protocol.bob2_protocol import Bob2Protocol
import socket
import random
import time
import threading

class Satellite:
    def __init__(self, listen_ip, listen_port, next_sat_ip, next_sat_port):
        self.protocol = Bob2Protocol()
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.next_sat_ip = next_sat_ip
        self.next_sat_port = next_sat_port

        # Setup IPv6 UDP socket
        self.sock = socket.socket(socket.AF_INET4, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.sock.bind((listen_ip, listen_port))

    def simulate_starlink_delay(self):
        """Simulate StarLink transmission delay with jitter"""
        base_delay = random.uniform(40, 60)  # Base delay 40-60ms
        jitter = random.uniform(2, 8)  # Additional jitter 2-8ms
        return (base_delay + jitter) / 1000  # Convert to seconds

    def forward_message(self, message_data, parsed_message):
        """Forward message to next satellite after delay"""
        time.sleep(self.simulate_starlink_delay())

        try:
            # Rebuild message for next hop while preserving type and content
            forwarded_message = self.protocol.build_message(
                message_type=parsed_message["message_type"],
                dest_ipv6=self.next_sat_ip,
                dest_port=self.next_sat_port,
                message_content=parsed_message["message_content"]
            )

            self.sock.sendto(forwarded_message, (self.next_sat_ip, self.next_sat_port))
            print(f"Forwarded message type {parsed_message['message_type']} to {self.next_sat_ip}")

        except Exception as e:
            print(f"Error forwarding message: {e}")

    def start_relay(self):
        """Start listening for and forwarding messages"""
        print(f"Satellite relay listening on [{self.listen_ip}]:{self.listen_port}")

        try:
            while True:
                message_data, addr = self.sock.recvfrom(4096)
                print(f"Received message from {addr}")

                try:
                    parsed = self.protocol.parse_message(message_data)
                    print(f"Message type: {parsed['message_type']}")
                    print(f"Content: {parsed['message_content']}")

                    # Handle message forwarding in separate thread
                    threading.Thread(
                        target=self.forward_message,
                        args=(message_data, parsed)
                    ).start()

                except ValueError as e:
                    print(f"Error parsing message: {e}")

        except KeyboardInterrupt:
            print("\nRelay stopped by user")
        finally:
            self.sock.close()

if __name__ == "__main__":
    # Example configuration for a relay satellite
    LISTEN_IP = "localhost"
    LISTEN_PORT = 12345
    NEXT_SAT_IP = "127.0.0.1"
    NEXT_SAT_PORT = 12346

    satellite = Satellite(LISTEN_IP, LISTEN_PORT, NEXT_SAT_IP, NEXT_SAT_PORT)
    satellite.start_relay()