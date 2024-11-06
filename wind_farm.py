from bob2_protocol import Bob2Protocol
import time
import random
import socket


class WindTurbineNode:
    def __init__(self, listen_ip, listen_port,sat_ip, sat_port):
        self.protocol = Bob2Protocol()

        self.sat_host = sat_ip
        self.sat_port = sat_port

        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.sock.bind((listen_ip, listen_port))

    def generate_turbine_data(self):
        """Simulate wind turbine sensor data"""
        return {
            "wind_speed": round(random.uniform(0, 25), 2),  # m/s
            "power_output": round(random.uniform(0, 5000), 2),  # kW
            "rotor_speed": round(random.uniform(5, 15), 2),  # rpm
            "blade_pitch": round(random.uniform(0, 90), 2),  # degrees
            "nacelle_orientation": round(random.uniform(0, 360), 2),  # degrees
            "vibration_level": round(random.uniform(0, 1), 3),  # normalized
            "timestamp": time.time()
        }

    def send_status_update(self):
        """Send turbine status to satellite"""
        turbine_data = self.generate_turbine_data()
        message_content = str(turbine_data)

        try:
            # Message type 0 for normal status update
            message = self.protocol.build_message(
                message_type=0,
                dest_ipv6=self.sat_host,
                dest_port=self.sat_port,
                message_content=message_content
            )
            self.sock.sendto(message, (self.sat_host, self.sat_port))
            return message
        except ValueError as e:
            print(f"Error building message: {e}")
            return None

    def send_alert(self, alert_type):
        """Send emergency alert to satellite"""
        alert_message = {
            "alert_type": alert_type,
            "timestamp": time.time()
        }

        try:
            message = self.protocol.build_message(
                message_type=1,
                dest_ipv6=self.sat_host,
                dest_port=self.sat_port,
                message_content=str(alert_message)
            )
            self.sock.sendto(message, (self.sat_host, self.sat_port))
            return message
        except ValueError as e:
            print(f"Error sending alert: {e}")
            return None

if __name__ == "__main__":
    turbine = WindTurbineNode("::", 12345, "fd00::1", 54321)

    # Simulation loop
    try:
        while True:
            # Send regular status update
            message = turbine.send_status_update()
            if message:
                parsed = turbine.protocol.parse_message(message)
                print("Status Update Sent:", parsed["message_content"])

            # Simulate random alert (1% chance)
            if random.random() < 0.01:
                alert_types = ["high_wind", "excessive_vibration", "grid_disconnect"]
                alert = turbine.send_alert(random.choice(alert_types))
                if alert:
                    parsed = turbine.protocol.parse_message(alert)
                    print("Alert Sent:", parsed["message_content"])

            time.sleep(5)
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")