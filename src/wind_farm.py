import time
import json
import random
import requests
import csv
import os

from find_shortest_way import find_shortest_path
import protocol.headers as bobb
import rsa


class WindTurbineNode:
    def __init__(self, device_list_path, connection_list_path):
        self.device_list_path = device_list_path
        self.connection_list_path = connection_list_path
        self.wf_id, self.wf_host = self.load_device_by_name("Offshore Windfarm")
        self.gs_id, self.gs_host = self.load_device_by_name("Ground Station")
        self.activate_device()

        self.public_key = self.load_key()

        self.next_satellite, self.shortest_path = self.load_nearest_satellite()
        print(self.wf_host, self.shortest_path, self.next_satellite)
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
        shortest_path = find_shortest_path(self.connection_list_path, self.wf_id, self.gs_id, broken_devices)
        
        if shortest_path is None:
            return None, None
        
        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        return next_sat_host, shortest_path
    

    def update_nearest_satellite(self):
        active_devices, broken_devices = self.get_active_devices()
        shortest_path = find_shortest_path(self.connection_list_path, self.wf_id, self.gs_id, broken_devices)

        if shortest_path is None:
            self.next_satellite = None
            self.shortest_path = None
            return
        
        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        self.next_satellite = next_sat_host
        self.shortest_path = shortest_path
    

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


    def send_status_update(self):
        """Send turbine status to the closest available satellite using HTTP"""
        self.update_nearest_satellite()
        if self.next_satellite is None:
            print("No satellites online. No message sent...")
            return
        turbine_data = self.generate_turbine_data()
        
        message_content = self.encrypt_turbine_data(turbine_data)

        # Build bobb headers
        header = bobb.BobbHeaders()
        header.source_ipv4 = self.wf_host[0]
        header.source_port = self.wf_host[1]
        header.dest_ipv4 = self.next_satellite[0]
        header.dest_port = self.next_satellite[1]
        header.sequence_number = 0
        header.message_type = 0

        # Build optional headers
        opt_header = bobb.BobbOptionalHeaders()

        # Serialize headers to hex
        bobb_header_hex = header.build_header().hex()
        bobb_optional_header_hex = opt_header.build_optional_header().hex()

        # Prepare headers for the HTTP request
        headers = {
            'X-Bobb-Header': bobb_header_hex,
            'X-Bobb-Optional-Header': bobb_optional_header_hex
        }

        # Send HTTP POST request to the next satellite
        url = f"http://{self.next_satellite[0]}:{self.next_satellite[1]}/"
        try:
            response = requests.post(url, headers=headers, data=message_content, verify=False)
            print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to", self.next_satellite)
            print("\033[91mResponse Received:\033[0m", response.status_code, response.text)
        except Exception as e:
            print(f"Error sending status update: {e}")


if __name__ == "__main__":
    try:
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
        devices = os.path.join(base_path, "devices_ip.csv")
        connections = os.path.join(base_path, "distances_common.csv")

        turbine = WindTurbineNode(devices, connections)
        input("Wind Turbine Online. Press any key to start...")

        # Simulation loop
        while True:
            # Send regular status update
            message = turbine.send_status_update()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    finally:
        turbine.deactivate_device()