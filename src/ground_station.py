import csv
import os
import time
import json
import rsa
import threading

from flask import Flask, request, jsonify

class GroundStationNode:
    def __init__(self, device_list_path, connection_list_path):
        self.device_list_path = device_list_path
        self.connection_list_path = connection_list_path
        self.name = "Ground Station"
        self.gs_id, self.gs_host = self.load_device_by_name(self.name)
        self.activate_device()

        self.private_key = self.load_key(private=True)

        self.app = Flask(self.name)

        @self.app.route('/', methods=['GET'])
        def get_device():
            return jsonify({"device-type": self.name, "device-id": self.gs_id, "group-id": 8})

        @self.app.route('/', methods=['POST'])
        def receive_data():
            data = self.decrypt_turbine_data(request.data)

            end_to_end_delay = time.time() - data['timestamp']
            print(f"End-to-end delay: {end_to_end_delay:.4f}s")
            print(f"Data received at Ground Station")
            print(f"\033[92mData: {data}\033[0m")

            # Define threshold values
            thresholds = {
                "wind_speed": 5.0,       # Example threshold for wind speed in m/s
                "power_output": 1200.0,   # Example threshold for power output in kW
                "rotor_speed": 10.0,      # Example threshold for rotor speed in rpm
                "blade_pitch": 75.0,      # Example threshold for blade pitch in degrees
                "nacelle_orientation": 300.0,  # Example threshold for nacelle orientation in degrees
                "vibration_level": 0.8    # Example threshold for vibration level (normalized)
            }

            # Check if any parameter exceeds the threshold
            alerts = {}
            for param, threshold in thresholds.items():
                if param in data and data[param] > threshold:
                    alerts[param] = f"{data[param]} exceeds threshold {threshold}"

            # Return the appropriate response based on checks
            if not alerts:
                print(f'"message": "OK - All parameters within safe thresholds"')
            else:
                print(f'"message": "Alert - Parameters exceeded thresholds", "alerts": {alerts}')
            return jsonify({"message": "Data received at Ground Station"})


    def activate_device(self):
        with open(self.device_list_path, 'r', newline='') as device_file:
            device_dict = csv.DictReader(device_file)
            devices = list(device_dict)
            fields = device_dict.fieldnames

        for device in devices:
            if int(device["id"]) == self.gs_id:
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
            if int(device["id"]) == self.gs_id:
                device['status'] = 0
        
        with open(self.device_list_path, 'w', newline='') as device_file:
            device_writer = csv.DictWriter(device_file, fields)
            device_writer.writeheader()
            device_writer.writerows(devices)
    

    def decrypt_turbine_data(self, encrypted_message):
        ### need to start splitting the message up into chunks if message size > 245 bytes
        encrypted_message = rsa.decrypt(encrypted_message, self.private_key)
        text = encrypted_message.decode("utf-8")
        message = json.loads(text)
        return message
    

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


    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.gs_host[0],
            "port": self.gs_host[1],
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

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)
    finally:
        ground_station.deactivate_device()