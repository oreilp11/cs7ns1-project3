import csv
import os
import time
from flask import Flask, request, jsonify
import threading

import protocol.headers as bobb


class GroundStationNode:
    def __init__(self, device_list_path, connection_list_path):
        self.device_list_path = device_list_path
        self.connection_list_path = connection_list_path
        self.name = "Ground Station"
        self.sat_host = self.load_network()
        self.app = Flask("GroundStation")

        @self.app.route('/', methods=['GET'])
        def receive_data():
            headers = request.headers
            data = request.data
            bobb_header_hex = headers.get('X-Bobb-Header')
            bobb_optional_header_hex = headers.get('X-Bobb-Optional-Header')

            # Parse headers using bobb
            header = bobb.BobbHeaders()
            header.parse_header(bytes.fromhex(bobb_header_hex))

            opt_header = bobb.BobbOptionalHeaders()
            opt_header.parse_optional_header(bytes.fromhex(bobb_optional_header_hex))

            end_to_end_delay = time.time() - opt_header.timestamp
            print(f"End-to-end delay: {end_to_end_delay:.4f}s")
            print(f"Data received at Ground Station from {header.source_ipv6}")
            print(f"\033[92mData: {data}\033[0m")
            return jsonify({"message": "Data received at Ground Station"})

    def load_network(self):
        current_device = ()
        with open(self.device_list_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['name'] == self.name:
                    current_device = (row['ip'], int(row['port']))
        return current_device

    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.sat_host[0],
            "port": self.sat_host[1],
            "use_reloader": False,
            "debug": False
        }, daemon=True).start()

if __name__ == "__main__":
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
    devices = os.path.join(base_path, "devices_ip.csv")
    connections = os.path.join(base_path, "distances_common.csv")

    ground_station = GroundStationNode(devices, connections)
    ground_station.start_flask_app()
    print("Ground Station Online.")
    while True:
        pass