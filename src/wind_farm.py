import time
import random
import socket
import csv
import os

from find_shortest_way import find_shortest_path
#from bob2_protocol import Bob2Protocol
from bob2_ipv4 import Bob2Protocol

class WindTurbineNode:
    def __init__(self, device_list_path, connection_list_path):
        self.device_list_path = device_list_path
        self.connection_list_path = connection_list_path
        self.protocol = Bob2Protocol()
        self.wf_host, self.next_satellite, self.shortest_path = self.load_network()
        print(self.wf_host, self.shortest_path, self.next_satellite)

        #self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.wf_host)

        print(f"Wind Turbine Node listening on {self.wf_host}")

    def load_network(self):
        windfarm = ()
        shortest_path = find_shortest_path(self.connection_list_path, 0, -1)
        # print(shortest_path)
        # open csv file to find windfarm ip and port
        with open(self.device_list_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            # header is id, name, ip, port. shortes_path give a list of id, we need to find the ip and port of the windfarm
            for row in reader:
                if int(row['id']) == shortest_path[0]:
                    windfarm = (row['ip'], int(row['port']))
                elif int(row['id']) == shortest_path[1]:
                    next_satellite = (row['ip'], int(row['port']))
        return windfarm, next_satellite, shortest_path

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
        # message = self.protocol.build_message(
        #     message_type=0,
        #     dest_ipv6="::1",
        #     dest_port=self.next_satellite[1],
        #     source_ipv6="::1",
        #     source_port=self.wf_host[1],
        #     sequence_number=0,
        #     message_content=message_content
        # )

        message = self.protocol.build_message(
            message_type=0,
            dest_ipv4=self.next_satellite[0],
            dest_port=self.next_satellite[1],
            source_ipv4=self.wf_host[0],
            source_port=self.wf_host[1],
            sequence_number=0,
            message_content=message_content
        )

        self.sock.sendto(message, self.next_satellite)
        print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to ", self.next_satellite)
        self.sock.settimeout(2)
        try:
            response, _ = self.sock.recvfrom(1024)
            # If response is received, assume success
            print("\033[91mAcknowledgment Received:\033[0m", self.protocol.parse_message(response))
            return message
        except socket.timeout:
            ValueError("No response received")
        

if __name__ == "__main__":
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
    devices = os.path.join(base_path, "devices_ipv4.csv")
    connections = os.path.join(base_path, "distances_common.csv")

    turbine = WindTurbineNode(devices, connections)
    input("Wind Turbine Online. Press any key to start...")

    # Simulation loop
    try:
        while True:
            # Send regular status update
            message = turbine.send_status_update()
            if message:
                parsed = turbine.protocol.parse_message(message)

            time.sleep(5)
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")