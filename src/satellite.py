import csv
import random
import time
import threading
import requests
import os
import sys

from flask import Flask, request, jsonify
from find_shortest_way import find_shortest_path
import update_satellite_positions
import network_manager

class Satellite:
    def __init__(self, sat_id):
        self.sat_id = int(sat_id)
        self.name = f"Satellite {self.sat_id}"
        self.sat_host = ('0.0.0.0', 33000 + self.sat_id)

        self.gs_id = -1
        self.wf_id = 0

        # Initialize Flask app
        self.app = Flask(self.name)

        # routing_table is dictionary of device_id to (host, port) tuple
        self.routing_table = network_manager.scan_network(device_id=self.sat_id,device_port=self.sat_host[1])
        self.routing_table[self.sat_id] = self.sat_host

        print(f"Routing table for {self.name}: {self.routing_table}")
        # Setup routes
        @self.app.route('/', methods=['GET'])
        def get_device():
            # Add device to routing table
            device_id = int(request.args.get('device-id'))
            device_port = request.args.get('device-port')
            self.routing_table[device_id] = (request.remote_addr, device_port)
            print(f"Added device {device_id} to routing table: {request.remote_addr}:{device_port}")
            return jsonify({
                "device-type": 1,
                "device-id": self.sat_id,
                "group-id": 8,
            })

        @self.app.route('/down', methods=['GET'])
        def remove_device():
            # Remove device from routing table
            device_id = int(request.args.get('device-id'))
            if device_id in self.routing_table:
                del self.routing_table[device_id]
                print(f"Removed device {device_id} from routing table")
            print(f"Routing table for {self.name}: {self.routing_table}")
            return jsonify({
                "message": f"Device {device_id} removed from routing table"
            })

        @self.app.route('/', methods=['POST'])
        def receive_data():
            headers = request.headers
            data = request.data
            print(f"Data received at Satellite {self.sat_id} : {data}")

            # Forward data to the next device
            threading.Thread(target=self.forward_data, args=(headers,data)).start()
            return jsonify({"message": f"Satellite {self.sat_id} received data"})

        print(f"{self.name} listening on {self.sat_host}")

    def update_nearest_satellite(self):
        self.satellites_positions = update_satellite_positions.calculate_satellite_positions(self.routing_table.keys())
        shortest_path, next_sat_distance = find_shortest_path(self.satellites_positions, self.sat_id, self.gs_id)

        if shortest_path is None:
            self.next_device = None
            self.shortest_path = None
            self.distance = None
            return

        next_sat_host = self.routing_table[shortest_path[1]]
        self.next_device = next_sat_host
        self.shortest_path = shortest_path
        self.distance = next_sat_distance


    def simulate_leo_delay(self):
        """Simulate LEO transmission delay with jitter"""
        C = 299_792_458 / 1000.0*1000.0  # kilometres per millisecond
        base_delay = self.distance / C # milliseconds
        jitter = random.uniform(2, 8) # milliseconds
        leo_delay = (base_delay + jitter) / 1000 # seconds
        print(f"Adding {leo_delay:0.4f}s delay")
        return leo_delay


    def forward_data(self, headers, data):
        # Simulate delay
        self.update_nearest_satellite()
        time.sleep(self.simulate_leo_delay())

        if 'X-Destination-ID' in headers:
            print(f"\n-----\nDestination ID: {headers['X-Destination-ID']}\n-----\n")

        if not self.next_device:
            print("No next device to forward the message.")
            return

        try:
            next_ip, next_port = self.next_device
            # Forward the HTTP request to the next device
            response = requests.post(f"http://{next_ip}:{next_port}/", headers=headers, data=data, verify=False,proxies={"http": None, "https": None})
            print(f"Forwarded data to {next_ip}:{next_port}, response: {response.status_code}")
        except Exception as e:
            print(f"Error forwarding data: {e}")
            network_manager.send_down_device(self.routing_table, self.shortest_path[1],self.sat_id)
            print(f"Removed satellite {self.shortest_path[1]} from routing table")
            self.forward_data(headers, data)

    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.sat_host[0],
            "port": self.sat_host[1],
            "use_reloader": False,
            "debug": False
        }, daemon=True).start()


if __name__ == "__main__":
    try:
        # Usage: python satellite.py <Satellite Name>
        if len(sys.argv) != 2:
            print("Usage: python satellite.py <Satellite id>")
            sys.exit(1)

        sat_id = sys.argv[1]

        satellite = Satellite(sat_id)
        satellite.start_flask_app()
        print(f"Satellite {sat_id} Online.")
        while True:
            # satellite.update_nearest_satellite()
            time.sleep(5)
    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)

