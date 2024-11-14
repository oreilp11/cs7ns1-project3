import time
import json
import random
import requests
import csv
import os

from flask import Flask, request, jsonify
from find_shortest_way import find_shortest_path
import rsa
import threading
import update_cluster_positions


class WindTurbineNode:
    def __init__(self, device_list_path, clusters_positions):
        self.device_list_path = device_list_path
        self.name = "Offshore Windfarm"
        self.wf_id, self.wf_host = self.load_device_by_name(self.name)
        self.gs_id, self.gs_host = self.load_device_by_name("Ground Station")
        
        self.latitude, self.longitude, self.altitude = None, None, None
        self.clusters_positions = clusters_positions
        for cluster in clusters_positions: 
            if cluster['id'] == self.wf_id:
                self.latitude, self.longitude, self.altitude = cluster['lat'], cluster['long'], cluster['alt']
        
        self.activate_device()
        self.public_key = self.load_key()

        self.next_satellite, self.distance, self.shortest_path = self.load_nearest_satellite()
        print(self.wf_host, self.shortest_path, self.next_satellite)

        self.app = Flask(self.name)

        @self.app.route('/', methods=['GET'])
        def get_device():
            return jsonify({
                "device-type": 0,
                "device-id": self.wf_id, 
                "group-id": 8, 
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude
            })

        if self.next_satellite is not None:
            print(f"Wind Turbine Node ready to send data to {self.next_satellite}")
        else:
            print("No satellites online yet.")


    def activate_device(self):
        with open(self.device_list_path, 'r', newline='') as device_file:
            device_dict = csv.DictReader(device_file)
            devices = list(device_dict)
            fields = device_dict.fieldnames

        for device in devices:
            if int(device["id"]) == self.wf_id:
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
            if int(device["id"]) == self.wf_id:
                device['status'] = 0

        with open(self.device_list_path, 'w', newline='') as device_file:
            device_writer = csv.DictWriter(device_file, fields)
            device_writer.writeheader()
            device_writer.writerows(devices)


    def load_key(self, private=False):
        keypath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys")

        if private:
            with open(os.path.join(keypath,'private.pem'), 'r') as keyfile:
                key = rsa.PrivateKey.load_pkcs1(keyfile.read())
        else:
            with open(os.path.join(keypath,'public.pem'), 'r') as keyfile:
                key = rsa.PublicKey.load_pkcs1(keyfile.read())
        return key


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
        shortest_path, next_sat_distance = find_shortest_path(self.clusters_positions, self.wf_id, self.gs_id, broken_devices)

        if shortest_path is None:
            return None, None, None

        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        return next_sat_host, next_sat_distance, shortest_path


    def update_nearest_satellite(self):
        active_devices, broken_devices = self.get_active_devices()
        shortest_path, next_sat_distance = find_shortest_path(self.clusters_positions, self.wf_id, self.gs_id, broken_devices)

        if shortest_path is None:
            self.next_satellite = None
            self.shortest_path = None
            self.distance = None
            return

        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        self.next_satellite = next_sat_host
        self.shortest_path = shortest_path
        self.distance = next_sat_distance


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


    def encrypt_turbine_data(self, message: dict):
        ### need to start splitting the message up into chunks if message size > 245 bytes
        text = json.dumps(message)
        utf8_text = text.encode("utf-8")
        encrypted_message = rsa.encrypt(utf8_text, self.public_key)
        return encrypted_message


    def simulate_leo_delay(self):
        """Simulate LEO transmission delay with jitter"""
        C = 299_792_458 / 1000.0*1000.0  # kilometres per millisecond
        base_delay = self.distance / C # milliseconds
        jitter = random.uniform(2, 8) # milliseconds
        leo_delay = (base_delay + jitter) / 1000 # seconds
        print(f"Adding {leo_delay:0.4f}s delay")
        return leo_delay


    def send_status_update(self):
        """Send turbine status to the closest available satellite using HTTP"""
        self.update_nearest_satellite()
        if self.next_satellite is None:
            print("No satellites online. No message sent...")
            return
        turbine_data = self.generate_turbine_data()

        message_content = self.encrypt_turbine_data(turbine_data)

        headers = {}
        time.sleep(self.simulate_leo_delay())
        # Send HTTP POST request to the next satellite
        url = f"http://{self.next_satellite[0]}:{self.next_satellite[1]}/"
        try:
            response = requests.post(url, headers=headers, data=message_content, verify=False)
            print(response.headers)
            print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to", self.next_satellite)
            print("\033[91mResponse Received:\033[0m", response.status_code, response.text)
        except Exception as e:
            print(f"Error sending status update: {e}")

    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.wf_host[0],
            "port": self.wf_host[1],
            "use_reloader": False,
            "debug": False
        }, daemon=True).start()


if __name__ == "__main__":
    try:
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
        devices = os.path.join(base_path, "devices_ip.csv")
        clusters_positions = update_cluster_positions.calculate_cluster_positions()

        turbine = WindTurbineNode(devices, clusters_positions)
        turbine.start_flask_app()
        
        input("\n"+"-"*30+"\nWind Turbine Online. Press any key to start...\n"+"-"*30+"\n\n")

        # Simulation loop
        while True:
            # Send regular status update
            message = turbine.send_status_update()
            time.sleep(5)

    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)
    finally:
        turbine.deactivate_device()