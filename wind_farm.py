from bob2_protocol import Bob2Protocol
import time
import random
import socket
import csv


class WindTurbineNode:
    def __init__(self):
        self.protocol = Bob2Protocol()
        self.wf_host, self.satellites = self.load_network()
        print(self.wf_host,self.satellites)
        self.current_sat_index = 0
        if self.satellites:
            closest_satellite = self.satellites[self.current_sat_index]
            self.sat_host = closest_satellite[1]
            self.sat_port = closest_satellite[2]
        else:
            print("No satellites available")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.wf_host)

        print(f"Wind Turbine Node listening on {self.wf_host}")
        print(f"Closest Satellite: {self.sat_host}:{self.sat_port}")

    def load_network(self):
        windfarm = ()
        satellites = []
        with open('distances_common.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Device1'] == 'Offshore Windfarm':
                    satellites.append((float(row['Distance_km']), row['IP2'], int(row['Port2'])))
                    windfarm = (row['IP1'], int(row['Port1']))
        satellites.sort()
        return windfarm, satellites

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
        """Send turbine status to the closest available satellite"""
        turbine_data = self.generate_turbine_data()
        message_content = str(turbine_data)
        message = self.protocol.build_message(
            message_type=0,
            dest_ipv6="::1",
            dest_port=self.sat_port,
            message_content=message_content
        )
        self.sock.sendto(message, (self.sat_host, self.sat_port))
        print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to ", self.sat_host, ":", self.sat_port)
        # Wait for acknowledgment
        self.sock.settimeout(2)
        try:
            response, _ = self.sock.recvfrom(1024)
            # If response is received, assume success
            print("\033[91mAcknowledgment Received:\033[0m", self.protocol.parse_message(response))
            return message
        except socket.timeout:
            ValueError("No response received")

    def send_alert(self, alert_type):
        """Send emergency alert to the closest available satellite"""
        alert_message = {
            "alert_type": alert_type,
            "timestamp": time.time()
        }

        while self.current_sat_index < len(self.satellites):
            try:
                message = self.protocol.build_message(
                    message_type=1,
                    dest_ipv6=self.sat_host,
                    dest_port=self.sat_port,
                    message_content=str(alert_message)
                )
                self.sock.sendto(message, (self.sat_host, self.sat_port))

                # Set timeout and wait for acknowledgment
                self.sock.settimeout(2)
                try:
                    response, _ = self.sock.recvfrom(1024)
                    # If response is received, assume success
                    return message
                except socket.timeout:
                    # No response received, try next satellite
                    pass
                finally:
                    self.sock.settimeout(None)  # Reset timeout
            except ValueError:
                pass  # Handle any value errors
            # Satellite didn't respond, try the next closest
            self.current_sat_index += 1
            if self.current_sat_index < len(self.satellites):
                next_satellite = self.satellites[self.current_sat_index]
                self.sat_host = next_satellite[1]
                self.sat_port = next_satellite[2]
            else:
                print("All satellites are unresponsive.")
                break
        return None

if __name__ == "__main__":
    turbine = WindTurbineNode()

    # Simulation loop
    try:
        while True:
            # Send regular status update
            message = turbine.send_status_update()
            if message:
                parsed = turbine.protocol.parse_message(message)

            # Simulate random alert (1% chance)
            if random.random() < 0.000001:
                alert_types = ["high_wind", "excessive_vibration", "grid_disconnect"]
                alert = turbine.send_alert(random.choice(alert_types))
                if alert:
                    parsed = turbine.protocol.parse_message(alert)
                    print("Alert Sent:", parsed["message_content"])

            time.sleep(5)
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")