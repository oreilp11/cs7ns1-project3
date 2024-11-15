import time
import json
import random
import requests
import csv
import os

from flask import Flask, request, jsonify
from find_shortest_way import find_shortest_path, find_second_shortest_path
import rsa
import threading
import update_satellite_positions
import uuid
from wind_turbine_calculator import WindTurbineCalculator

class WindTurbineNode:
    def __init__(self, device_list_path, satellites_positions):
        self.device_list_path = device_list_path
        self.name = "Offshore Windfarm"
        self.wf_id, self.wf_host = self.load_device_by_name(self.name)
        self.gs_id, self.gs_host = self.load_device_by_name("Ground Station")

        # Get turbine position from satellites_positions
        self.latitude, self.longitude, self.altitude = None, None, None
        self.satellites_positions = satellites_positions
        for satellite in satellites_positions:
            if satellite['id'] == self.wf_id:
                self.latitude, self.longitude, self.altitude = satellite['lat'], satellite['long'], satellite['alt']

        # Initialize wind turbine calculator
        self.turbine = WindTurbineCalculator()

        self.activate_device()
        self.public_key = self.load_key()

        self.next_satellite, self.distance, self.shortest_path, self.second_next_satellite, self.second_distance, self.second_shortest_path = self.load_nearest_satellite()
        print(self.wf_host, self.shortest_path, self.next_satellite)
        print(self.wf_host, self.second_shortest_path, self.second_next_satellite)

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

        if self.second_next_satellite is not None:
            print(f"Wind Turbine Node ready to send data to {self.second_next_satellite}")
        else:
            print("No second satellites online yet.")


    def get_weather_data(self):
        """Get real weather data from Open-Meteo API with added jitter for realism"""
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current=temperature_2m,surface_pressure,wind_speed_10m"

        try:
            response = requests.get(url)
            data = response.json()
            current = data['current']
            print(current)

            # Get current weather data with small random variations
            temperature = current['temperature_2m'] + random.uniform(-0.5, 0.5)  # ±0.5°C jitter
            wind_speed = (current['wind_speed_10m'] / 3.6) + random.uniform(-0.3, 0.3)  # ±0.3 m/s jitter
            print("real wind speed", current['wind_speed_10m']/3.6)
            print("wind speed", wind_speed)
            pressure = (current['surface_pressure'] * 100) + random.uniform(-50, 50)  # ±50 Pa jitter

            # Ensure non-zero physical variables don't go below 0
            wind_speed = max(0, wind_speed)
            pressure = max(0, pressure)

            return {
                'wind_speed': wind_speed,
                'temperature': temperature,
                'pressure': pressure
            }

        except Exception as e:
            print(f"Weather API error: {e}")
            return None

    def generate_turbine_data(self):
        """Generate wind turbine sensor data using simplified calculator"""
        try:
            # Get weather data
            weather_data = self.get_weather_data()
            if weather_data is None:
                raise Exception("No weather data available")

            # Calculate power output
            power_output = self.turbine.estimate_power_output(
                wind_speed=weather_data['wind_speed'],
                temperature_celsius=weather_data['temperature'],
                pressure_pascal=weather_data['pressure']
            )

            return {
                "temperature": round(weather_data['temperature'], 2),
                "pressure": round(weather_data['pressure'], 2),
                "wind_speed": round(weather_data['wind_speed'], 2),
                "power_output": round(power_output, 2),
                "timestamp": time.time(),
                "turbine_id": self.wf_id,
                "uid": str(uuid.uuid4()),
                "turbine_id": self.wf_id
            }

        except Exception as e:
            print(f"Error generating turbine data: {e}")
            # Fallback to random data if simulation fails
            return {
                "temperature": round(random.uniform(-10, 40), 2),
                "pressure": round(random.uniform(900, 1100), 2),
                "wind_speed": round(random.uniform(0, 25), 2),
                "power_output": round(random.uniform(0, 5000), 2),
                "timestamp": time.time(),
                "turbine_id": self.wf_id,
                "uid": str(uuid.uuid4()),
                "turbine_id": self.wf_id
            }


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
        shortest_path, next_sat_distance = find_shortest_path(self.satellites_positions, self.wf_id, self.gs_id, broken_devices)
        second_shortest_path, second_next_sat_distance = find_second_shortest_path(self.satellites_positions, self.wf_id, self.gs_id, broken_devices)

        if shortest_path is None:
            return None, None, None, None, None, None

        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        second_next_sat_name, second_next_sat_host = self.load_device_by_id(second_shortest_path[1])
        return next_sat_host, next_sat_distance, shortest_path, second_next_sat_host, second_next_sat_distance, second_shortest_path


    def update_nearest_satellite(self):
        active_devices, broken_devices = self.get_active_devices()
        shortest_path, next_sat_distance = find_shortest_path(self.satellites_positions, self.wf_id, self.gs_id, broken_devices)
        second_shortest_path, second_next_sat_distance = find_second_shortest_path(self.satellites_positions, self.wf_id, self.gs_id, broken_devices)

        if shortest_path is None:
            self.next_satellite = None
            self.shortest_path = None
            self.distance = None
            self.second_next_satellite = None
            self.second_shortest_path = None
            self.second_distance = None
            return

        next_sat_name, next_sat_host = self.load_device_by_id(shortest_path[1])
        second_next_sat_name, second_next_sat_host = self.load_device_by_id(second_shortest_path[1])
        self.next_satellite = next_sat_host
        self.shortest_path = shortest_path
        self.distance = next_sat_distance
        self.second_next_satellite = second_next_sat_host
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


    def encrypt_turbine_data(self, message: dict):
        ### need to start splitting the message up into chunks if message size > 245 bytes
        text = json.dumps(message)
        utf8_text = text.encode("utf-8")
        encrypted_message = rsa.encrypt(utf8_text, self.public_key)
        return encrypted_message


    def simulate_leo_delay(self, distance):
        """Simulate LEO transmission delay with jitter"""
        C = 299_792_458 / 1000.0*1000.0  # kilometres per millisecond
        base_delay = distance / C # milliseconds
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

        headers = {
            'X-Destination-ID': str(self.gs_id)
        }

        time.sleep(self.simulate_leo_delay(self.distance))
        # Send HTTP POST request to the next satellite
        url = f"http://{self.next_satellite[0]}:{self.next_satellite[1]}/"
        try:
            response = requests.post(url, headers=headers, data=message_content, verify=False)
            print(response.headers)
            print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to", self.next_satellite)
            print("\033[91mResponse Received:\033[0m", response.status_code, response.text)
        except Exception as e:
            print(f"Error sending status update: {e}")

        if self.second_next_satellite is None:
            print("No second satellites online. No message sent...")
            return

        time.sleep(self.simulate_leo_delay(self.second_distance))
        # Send HTTP POST request to the second next satellite
        second_url = f"http://{self.second_next_satellite[0]}:{self.second_next_satellite[1]}/"
        try:
            second_response = requests.post(second_url, headers=headers, data=message_content, verify=False)
            print(second_response.headers)
            print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to", self.second_next_satellite)
            print("\033[91mResponse Received:\033[0m", second_response.status_code, second_response.text)
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
        satellites_positions = update_satellite_positions.calculate_satellite_positions()

        turbine = WindTurbineNode(devices, satellites_positions)
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