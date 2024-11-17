import time
import json
import rsa
import threading
import os

from flask import Flask, request, jsonify
import update_satellite_positions
import network_manager

class GroundStationNode:
    def __init__(self):
        self.name = "Ground Station"
        self.gs_id = -1  # ground station always has ID -1
        self.gs_host = ('0.0.0.0', 33999)  # ground station always uses port 32999

        # Get position from static positions
        positions = update_satellite_positions.read_static_positions()
        self.latitude = positions[0]['lat']
        self.longitude = positions[0]['long']
        self.altitude = positions[0]['alt']

        self.private_key = self.load_key(private=True)

        # Announce presence to network
        network_manager.scan_network(device_id=self.gs_id, device_port=self.gs_host[1])

        self.app = Flask(self.name)

        @self.app.route('/', methods=['GET'])
        def get_device():
            return jsonify({
                "device-type": 2,
                "device-id": self.gs_id,
                "group-id": 8,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude
            })

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

    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.gs_host[0],
            "port": self.gs_host[1],
            "use_reloader": False,
            "debug": False
        }, daemon=True).start()


if __name__ == "__main__":
    try:
        ground_station = GroundStationNode()
        ground_station.start_flask_app()
        print("Ground Station Online.")

        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)
    finally:
        # Notify network that ground station is going offline
        network_manager.send_down_device({-1: ground_station.gs_host}, ground_station.gs_id)