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
            data = request.data
            data = self.hamming_decode_message(data)
            if data is None:
                print("Too many Errors, could not decode")
                print(f"Message: {request.data}")
                return jsonify({"message":"Too many Errors, could not decode"})
            
            data = self.decrypt_turbine_data(data)

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
            for turbine, vars in data['turbines'].items():
                for param, threshold in thresholds.items():
                    if param in vars and vars[param] > threshold:
                        alerts[turbine] = f"[{param}] {vars[param]} exceeds threshold {threshold}"

            # Return the appropriate response based on checks
            if not alerts:
                print(f'"message": "OK - All parameters within safe thresholds"')
            else:
                print(f'"message": "Alert - Parameters exceeded thresholds"')#, "alerts": {alerts}')
            return jsonify({"message": "Data received at Ground Station"})


    def decrypt_turbine_data(self, encrypted_message):
        decrypted_message = []
        for i in range(0, len(encrypted_message), 256):
            decrypted_message.append(rsa.decrypt(encrypted_message[i:i+256], self.private_key))
        decrypted_message = bytes(b''.join(decrypted_message))
        text = decrypted_message.decode("utf-8")
        message = json.loads(text)
        return message
    

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
        error_position = c1 * 1 + c2 * 2 + c3 * 4

        corrected = list(encoded)
        if error_position != 0:  # If there is an error
            error_index = error_position - 1
            corrected[error_index] = '1' if corrected[error_index] == '0' else '0'

        # Extract original data bits
        d1, d2, d3, d4 = corrected[2], corrected[4], corrected[5], corrected[6]
        return f"{d1}{d2}{d3}{d4}"


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