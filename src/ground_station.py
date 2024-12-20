import time
import json
import rsa
import threading
import os
import csv

from flask import Flask, request, jsonify
import update_satellite_positions
import network_manager
from wind_turbine_calculator import WindTurbineCalculator


class GroundStationNode:
    def __init__(self):
        self.name = "Ground Station"
        self.gs_id = -1  # ground station always has ID -1
        self.gs_host = ('0.0.0.0', 33999)  # ground station always uses port 33999

        # Get position from static positions
        positions = update_satellite_positions.read_static_positions()
        self.latitude = positions[0]['lat']
        self.longitude = positions[0]['long']
        self.altitude = positions[0]['alt']

        self.turbine_calc = WindTurbineCalculator()
        self.private_key = self.load_rsa_key(private=True)

        # # Announce presence to network
        network_manager.scan_network(device_id=self.gs_id, device_port=self.gs_host[1])

        self.app = Flask(self.name)

        # Initialize CSV file (erase if exists)
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.csv_file_path = os.path.join(data_dir, 'turbine_data.csv')
        if os.path.exists(self.csv_file_path):
            os.remove(self.csv_file_path)
            print(f"Erased existing CSV file at {self.csv_file_path}")
        # Create the CSV file with headers
        with open(self.csv_file_path, mode='w', newline='') as csvfile:
            fieldnames = ['timestamp', 'turbine_id', 'turbine', 'temperature', 'pressure', 'wind_speed', 'power_output']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            print(f"Created new CSV file at {self.csv_file_path}")

        @self.app.route('/', methods=['GET'])
        def get_device():
            return jsonify({
                "device-type": 2,
                "device-id": self.gs_id,
                "group-id": 8,
            })

        @self.app.route('/', methods=['POST'])
        def receive_data():
            noisy_data = request.data
            corrected_data = self.hamming_decode_message(noisy_data)
            decrypted_data = self.decrypt_rsa_turbine_data(corrected_data)

            if decrypted_data is None:
                print("Decryption failed or message is corrupted")
                return jsonify({"message":"Decryption failed or message is corrupted"})

            end_to_end_delay = time.time() - decrypted_data['timestamp']
            print(f"End-to-end delay: {end_to_end_delay:.4f}s")
            print(f"Data received at Ground Station")
            print(f"\033[92mData: {decrypted_data.keys()}\033[0m")

             # Write data to CSV file
            self.store_data_to_csv(decrypted_data)

            # Define threshold values
            thresholds = {
                "power_output": 200
            }

            # Check if any parameter exceeds the threshold
            alerts = {}
            for turbine, turbine_data in decrypted_data['turbines'].items():
                estimated_power = round(self.turbine_calc.estimate_power_output(turbine_data['wind_speed'], turbine_data['temperature'], turbine_data['pressure']), 2)
                actual_power = turbine_data['power_output'] 
                if abs(estimated_power-actual_power) > thresholds['power_output']:
                    alerts[turbine] = f"Expected {estimated_power}kW from local weather variables but received {actual_power}kW"

            # Return the appropriate response based on checks
            if alerts:
                print(f'"message": "Alert - Parameters exceeded thresholds"\n"Alerts": {alerts}')
            return jsonify({"message": "Data received at Ground Station"})


    def store_data_to_csv(self, data):
        """Store received data in a CSV file."""
        with open(self.csv_file_path, mode='a', newline='') as csvfile:
            fieldnames = ['timestamp', 'turbine_id', 'turbine', 'temperature', 'pressure', 'wind_speed', 'power_output']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            for turbine_name, turbine_data in data['turbines'].items():
                row = {
                    'timestamp': data['timestamp'],
                    'turbine_id': data['turbine_id'],
                    'turbine': turbine_name,
                    'temperature': turbine_data['temperature'],
                    'pressure': turbine_data['pressure'],
                    'wind_speed': turbine_data['wind_speed'],
                    'power_output': turbine_data['power_output']
                }
                writer.writerow(row)


    def decrypt_rsa_turbine_data(self, encrypted_message):
        try:
            decrypted_message = []
            for i in range(0, len(encrypted_message), 256):
                decrypted_message.append(rsa.decrypt(encrypted_message[i:i+256], self.private_key))
            decrypted_message = bytes(b''.join(decrypted_message))
            text = decrypted_message.decode("utf-8")
            message = json.loads(text)
            return message
        except (rsa.pkcs1.DecryptionError, UnicodeDecodeError, json.JSONDecodeError):
            return None


    def hamming_decode_message(self, encoded_data: bytes) -> bytes:
        decoded_nibbles = []

        # Convert bytes into bit strings
        bit_string = ''.join(f"{byte:08b}" for byte in encoded_data)

        # Process each 7-bit block
        for i in range(0, len(bit_string), 7):
            block = bit_string[i:i+7].ljust(7, '0')  # Ensure block is 7 bits
            decoded_nibble = self.hamming_decode(block)
            decoded_nibbles.append(decoded_nibble)

        # Combine decoded nibbles into bytes
        decoded_message = []
        for i in range(0, len(decoded_nibbles), 2):
            if i + 1 < len(decoded_nibbles):
                high_nibble = int(decoded_nibbles[i], 2) << 4
                low_nibble = int(decoded_nibbles[i + 1], 2)
                decoded_message.append(high_nibble | low_nibble)

        return bytes(decoded_message)


    def hamming_decode(str, encoded: str) -> str:
        """Decodes a byte message using Hamming (7,4) code and corrects errors where possible"""
        p1, p2, d1, p3, d2, d3, d4 = map(int, encoded)
        c1 = p1 ^ d1 ^ d2 ^ d4  # Syndrome bit 1
        c2 = p2 ^ d1 ^ d3 ^ d4  # Syndrome bit 2
        c3 = p3 ^ d2 ^ d3 ^ d4  # Syndrome bit 3
        err_pos = c1 * 1 + c2 * 2 + c3 * 4

        corrected = list(encoded)
        if err_pos != 0:  # If there is an error
            corrected[err_pos-1] = '1' if corrected[err_pos-1] == '0' else '0'

        # Extract original data bits
        d1, d2, d3, d4 = corrected[2], corrected[4], corrected[5], corrected[6]
        return f"{d1}{d2}{d3}{d4}"


    def load_rsa_key(self, private=False):
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