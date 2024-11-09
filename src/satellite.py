import csv
import socket
import random
import time
import threading
from flask import Flask, request, jsonify
import requests
import threading
import os
import sys
# Replace bob2 imports with bobb
# ...existing code...
bobb_protocol_path = os.path.abspath("../../bobb/src/utils/headers/")
sys.path.append(bobb_protocol_path)
import necessary_headers as bobb
import optional_header as bobb_optional

from find_shortest_way import find_shortest_path

class Satellite:
    def __init__(self, sat_id, device_list_path, connection_list_path):
        self.device_list_path = device_list_path
        self.connection_list_path = connection_list_path
        self.sat_id = int(sat_id)  # Ensure sat_id is an integer
        self.sat_host, self.next_device, self.shortest_path = self.load_network()
        self.name = f"Satellite {sat_id}"

        self.app = Flask(f"satellite_{sat_id}")

        @self.app.route('/', methods=['GET'])
        def receive_data():
            headers = request.headers
            bobb_header_hex = headers.get('X-Bobb-Header')
            bobb_optional_header_hex = headers.get('X-Bobb-Optional-Header')
            data = request.data
            print(f"Data received at Satellite {self.sat_id} : {data}")

            # Parse headers using bobb
            header = bobb.BobbHeaders()
            header.parse_header(bytes.fromhex(bobb_header_hex))

            opt_header = bobb_optional.BobbOptionalHeaders()
            opt_header.parse_optional_header(bytes.fromhex(bobb_optional_header_hex))

            # Forward data to the next device
            threading.Thread(target=self.forward_data, args=(headers,data)).start()
            return jsonify({"message": f"Satellite {self.sat_id} received data"})

        print(f"{self.name} listening on {self.sat_host}")
        print(f"Shortest path to Ground Station: {self.shortest_path}")
        print(f"Next device: {self.next_device}")

    def load_network(self):
        current_device = ()
        shortest_path = find_shortest_path(self.connection_list_path, self.sat_id, -1)
        # ...existing code...
        with open(self.device_list_path, 'r') as csvfile:
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

    def forward_data(self, headers, data):
        # Simulate delay
        time.sleep(self.simulate_starlink_delay())
        if self.next_device:
            try:
                next_ip, next_port = self.next_device
                # Forward the HTTP request to the next device
                response = requests.get(f"http://{next_ip}:{next_port}/", headers=headers, data=data,verify=False)
                print(f"Forwarded data to {next_ip}:{next_port}, response: {response.status_code}")
            except Exception as e:
                print(f"Error forwarding data: {e}")
        else:
            print("No next device to forward the message.")

    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.sat_host[0],
            "port": self.sat_host[1],
            "use_reloader": False,
            "debug": False
        }, daemon=True).start()

if __name__ == "__main__":


    # Usage: python satellite.py <Satellite Name>
    if len(sys.argv) != 2:
        print("Usage: python satellite.py <Satellite id>")
        sys.exit(1)

    sat_id = sys.argv[1]

    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
    devices = os.path.join(base_path, "devices_ip.csv")
    connections = os.path.join(base_path, "distances_common.csv")

    satellite = Satellite(sat_id, devices, connections)
    satellite.start_flask_app()
    print(f"Satellite {sat_id} Online.")
    # don't quit
    while True:
        pass

