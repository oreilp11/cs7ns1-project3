import csv
import random
import time
import threading
import requests
import os
import sys

from flask import Flask, request, jsonify
from find_shortest_way import find_shortest_path, find_second_shortest_path
import update_satellite_positions


class Satellite:
    def __init__(self, sat_id, device_list_path, satellites_positions):
        self.device_list_path = device_list_path
        self.wf_id, self.wf_host = self.load_device_by_name("Offshore Windfarm")
        self.gs_id, self.gs_host = self.load_device_by_name("Ground Station")
        self.sat_id = int(sat_id)  # Ensure sat_id is an integer
        self.name, self.sat_host = self.load_device_by_id(self.sat_id)

        self.latitude, self.longitude, self.altitude = None, None, None
        self.satellites_positions = satellites_positions
        for satellite in satellites_positions:
            if satellite['id'] == self.sat_id:
                self.latitude, self.longitude, self.altitude = satellite['lat'], satellite['long'], satellite['alt']

        self.activate_device()
        self.next_device, self.distance, self.shortest_path, self.second_next_device, self.second_distance, self.second_shortest_path = self.load_nearest_satellite()

        self.app = Flask(self.name)

        @self.app.route('/', methods=['GET'])
        def get_device():
            return jsonify({
                "device-type": 1,
                "device-id": self.wf_id,
                "group-id": 8,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude
            })

        @self.app.route('/', methods=['POST'])
        def receive_data():
            headers = request.headers
            data = request.data
            print(f"Data received at Satellite {self.sat_id} : {data}")

            # Forward data to the next device
            threading.Thread(target=self.forward_data, args=(headers, data)).start()
            return jsonify({"message": f"Satellite {self.sat_id} received data"})

        print(f"{self.name} listening on {self.sat_host}")
        print(f"Shortest path to Ground Station: {self.shortest_path}")
        print(f"Next device: {self.next_device}")
        print(f"Second shortest path to Ground Station: {self.second_shortest_path}")
        print(f"Second next device: {self.second_next_device}")


    def activate_device(self):
        with open(self.device_list_path, 'r', newline='') as device_file:
            device_dict = csv.DictReader(device_file)
            devices = list(device_dict)
            fields = device_dict.fieldnames

        for device in devices:
            if int(device["id"]) == self.sat_id:
                device['status'] = 1

        with open(self.device_list_path, 'w', newline='') as device_file:
            device_writer = csv.DictWriter(device_file, fields)
            device_writer.writeheader()
            device_writer.writerows(devices)


    def deactivate_device(self):
        with open(self.device_list_path, 'r', newline='') as device_file:
            device_dict = csv.DictReader(device_file)
            devices = list(device_dict)
            fields = device_dict.fieldnames

        for device in devices:
            if int(device["id"]) == self.sat_id:
                device['status'] = 0

        with open(self.device_list_path, 'w', newline='') as device_file:
            device_writer = csv.DictWriter(device_file, fields)
            device_writer.writeheader()
            device_writer.writerows(devices)


    def load_device_by_name(self, device_name):
        device_host = ()
        device_id = None
        with open(self.device_list_path, 'r') as device_file:
            device_dict = csv.DictReader(device_file)
            for device in device_dict:
                if device['name'] == device_name:
                    device_host = (device['ip'], int(device['port']))
                    device_id = int(device["id"])
        return device_id, device_host


    def load_device_by_id(self, device_id):
        device_host = ()
        device_name = None
        with open(self.device_list_path, 'r') as device_file:
            device_dict = csv.DictReader(device_file)
            for device in device_dict:
                if int(device['id'] )== device_id:
                    device_host = (device['ip'], int(device['port']))
                    device_name = device["name"]
        return device_name, device_host


    def load_nearest_satellite(self):
        active_devices, broken_devices = self.get_active_devices()
        shortest_path, next_sat_distance = find_shortest_path(self.satellites_positions, self.sat_id, self.gs_id, broken_devices)
        second_shortest_path, second_next_sat_distance = find_second_shortest_path(self.satellites_positions, self.sat_id, self.gs_id, broken_devices)

        if shortest_path is None:
            return None, None, None, None, None, None

        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        second_next_sat_name, second_next_sat_host = self.load_device_by_id(second_shortest_path[1])
        return next_sat_host, next_sat_distance, shortest_path, second_next_sat_host, second_next_sat_distance, second_shortest_path


    def update_nearest_satellite(self):
        active_devices, broken_devices = self.get_active_devices()
        shortest_path, next_sat_distance = find_shortest_path(self.satellites_positions, self.sat_id, self.gs_id, broken_devices)
        second_shortest_path, second_next_sat_distance = find_second_shortest_path(self.satellites_positions, self.sat_id, self.gs_id, broken_devices)

        if shortest_path is None:
            self.next_device = None
            self.shortest_path = None
            self.distance = None
            self.second_next_device = None
            self.second_shortest_path = None
            self.second_distance = None
            return

        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        second_next_sat_name, second_next_sat_host = self.load_device_by_id(second_shortest_path[1])
        self.next_device = next_sat_host
        self.shortest_path = shortest_path
        self.distance = next_sat_distance
        self.second_next_device = second_next_sat_host
        self.second_shortest_path = second_shortest_path
        self.second_distance = second_next_sat_distance


    def get_active_devices(self):
        active_devices = []
        broken_devices = []
        with open(self.device_list_path, 'r') as device_file:
            device_dict = csv.DictReader(device_file)
            for device in device_dict:
                if int(device['status']) == 1:
                    active_devices.append(device['id'])
                else:
                    broken_devices.append(device['id'])

        return active_devices, broken_devices


    def simulate_leo_delay(self, distance):
        """Simulate LEO transmission delay with jitter"""
        C = 299_792_458 / 1000.0*1000.0  # kilometres per millisecond
        base_delay = distance / C # milliseconds
        jitter = random.uniform(2, 8) # milliseconds
        leo_delay = (base_delay + jitter) / 1000 # seconds
        print(f"Adding {leo_delay:0.4f}s delay")
        return leo_delay


    def forward_data(self, headers, data):
        # Simulate delay for primary path
        time.sleep(self.simulate_leo_delay(self.distance))

        if 'X-Destination-ID' in headers:
            print(f"\n-----\nDestination ID: {headers['X-Destination-ID']}\n-----\n")

        if not self.next_device:
            print("No next device to forward the message.")
            return

        try:
            next_ip, next_port = self.next_device
            # Forward the HTTP request to the next device
            response = requests.post(f"http://{next_ip}:{next_port}/", headers=headers, data=data, verify=False)
            print(f"Forwarded data to {next_ip}:{next_port}, response: {response.status_code}")
        except Exception as e:
            print(f"Error forwarding data: {e}")


        # Simulate delay for secondary path
        time.sleep(self.simulate_leo_delay(self.second_distance))

        if not self.second_next_device:
            print("No second next device to forward the message.")
            return

        try:
            second_next_ip, second_next_port = self.second_next_device
            # Forward the HTTP request to the second next device
            response = requests.post(f"http://{second_next_ip}:{second_next_port}/", headers=headers, data=data, verify=False)
            print(f"Forwarded data to {second_next_ip}:{second_next_port}, response: {response.status_code}")
        except Exception as e:
            print(f"Error forwarding data: {e}")


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

        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
        devices = os.path.join(base_path, "devices_ip.csv")
        satellites_positions = update_satellite_positions.calculate_satellite_positions()

        satellite = Satellite(sat_id, devices, satellites_positions)
        satellite.start_flask_app()
        print(f"Satellite {sat_id} Online.")
        while True:
            satellite.update_nearest_satellite()
            time.sleep(5)
    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)
    finally:
        satellite.deactivate_device()
