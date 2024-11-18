import time
import json
import random
import requests
import os
import math

from flask import Flask, request, jsonify
from find_shortest_way import find_shortest_path
import rsa
import threading
import update_satellite_positions
from wind_turbine_calculator import WindTurbineCalculator
import network_manager


class WindTurbineNode:
    def __init__(self):
        self.name = "Offshore Windfarm"
        self.wf_id = 0  # wind farm always has ID 0
        self.wf_host = ('0.0.0.0', 33000)  # wind farm always uses port 33000
        self.gs_id = -1  # ground station always has ID -1

        # Initialize routing table
        self.routing_table = network_manager.scan_network(device_id=self.wf_id, device_port=self.wf_host[1])
        self.routing_table[self.wf_id] = self.wf_host
        print(f"Routing table for {self.name}: {self.routing_table}")

        self.turbine = WindTurbineCalculator()
        self.public_key = self.load_key()

        positions = update_satellite_positions.read_static_positions()
        self.latitude = positions[1]['lat']
        self.longitude = positions[1]['long']
        self.altitude = positions[1]['alt']

        self.app = Flask(self.name)

        @self.app.route('/', methods=['GET'])
        def get_device():
            # Add device to routing table
            time.sleep(self.simulate_leo_delay())
            device_id = int(request.args.get('device-id'))
            device_port = request.args.get('device-port')
            self.routing_table[device_id] = (request.remote_addr, int(device_port))
            print(f"Added device {device_id} to routing table: {request.remote_addr}:{device_port}")
            return jsonify({
                "device-type": 0,
                "device-id": self.wf_id,
                "group-id": 8,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude
            })

        @self.app.route('/down', methods=['GET'])
        def remove_device():
            # Remove device from routing table
            time.sleep(self.simulate_leo_delay())
            device_id = int(request.args.get('device-id'))
            if device_id in self.routing_table:
                del self.routing_table[device_id]
                print(f"Removed device {device_id} from routing table")
            print(f"Routing table for {self.name}: {self.routing_table}")
            return jsonify({
                "message": f"Device {device_id} removed from routing table"
            })


    def get_weather_data(self):
        """Get real weather data from Open-Meteo API with added jitter for realism"""
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current=temperature_2m,surface_pressure,wind_speed_10m"

        try:
            response = requests.get(url)
            data = response.json()
            current = data['current']

            # Get current weather data with small random variations
            temperature = current['temperature_2m'] + random.uniform(-0.5, 0.5)  # ±0.5°C jitter
            wind_speed = (current['wind_speed_10m'] / 3.6) + random.uniform(-0.3, 0.3)  # ±0.3 m/s jitter
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
                "turbine_id": self.wf_id
            }


    def load_key(self, private=False):
        keypath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys")

        if private:
            with open(os.path.join(keypath,'private.pem'), 'r') as keyfile:
                key = rsa.PrivateKey.load_pkcs1(keyfile.read())
        else:
            with open(os.path.join(keypath,'public.pem'), 'r') as keyfile:
                key = rsa.PublicKey.load_pkcs1(keyfile.read())
        return key


    def update_nearest_satellite(self):
        self.satellites_positions = update_satellite_positions.calculate_satellite_positions(self.routing_table.keys())
        shortest_path, next_sat_distance = find_shortest_path(self.satellites_positions, self.wf_id, self.gs_id)

        if shortest_path is None:
            self.next_satellite = None
            self.shortest_path = None
            self.distance = None
            return

        next_sat_id = shortest_path[1]
        if next_sat_id in self.routing_table:
            self.next_satellite = self.routing_table[next_sat_id]
            self.shortest_path = shortest_path
            self.distance = next_sat_distance
        else:
            self.next_satellite = None
            self.shortest_path = None
            self.distance = None


    def encrypt_turbine_data(self, message: dict):
        ### need to start splitting the message up into chunks if message size > 245 bytes
        text = json.dumps(message)
        utf8_text = text.encode("utf-8")
        encrypted_message = rsa.encrypt(utf8_text, self.public_key)
        return encrypted_message


    def hamming_encode(self, data: str) -> str:
        """Encodes a 4-bit binary string using Hamming (7,4) code."""
        d1, d2, d3, d4 = map(int, data)
        p1 = d1 ^ d2 ^ d4  # Parity 1
        p2 = d1 ^ d3 ^ d4  # Parity 2
        p3 = d2 ^ d3 ^ d4  # Parity 3
        return f"{p1}{p2}{d1}{p3}{d2}{d3}{d4}"


    def hamming_encode_message(self, data: bytes) -> bytes:
        """Encodes a byte message using Hamming (7,4) code."""
        encoded_bits = []
        for byte in data:
            tophalf = (byte >> 4) & 0xF  # Upper 4 bits
            encoded_bits.append(self.hamming_encode(f"{tophalf:04b}"))
            bottomhalf = byte & 0xF      # Lower 4 bits
            encoded_bits.append(self.hamming_encode(f"{bottomhalf:04b}"))

        encoded_message = []
        current_byte:str = ""
        for bit_group in encoded_bits:
            current_byte += bit_group
            while len(current_byte) >= 8:
                encoded_message.append(int(current_byte[:8], 2))
                current_byte = current_byte[8:]
        if current_byte:
            encoded_message.append(int(current_byte.ljust(8, "0"), 2))
        return bytes(encoded_message)


    def simulate_leo_delay(self) -> float:
        """Simulate LEO transmission delay with jitter"""
        C = 299_792_458 / 1000.0*1000.0  # kilometres per millisecond
        base_delay = self.distance / C # milliseconds
        jitter = random.uniform(2, 8) # milliseconds
        leo_delay = (base_delay + jitter) / 1000 # seconds
        print(f"Adding {leo_delay:0.4f}s delay")
        return leo_delay


    def simulate_noise(self, data: bytes) -> bytes:
        """Simulate LEO transmission delay with jitter"""
        f = 30e9 # GHz
        C = 3e8 # m/s^2
        Pt = 50 # Watts
        Pt = 10*math.log10(Pt) + 30
        L = 20*math.log10(self.distance*1000*f*4*math.pi/C)
        Pr = 10**(-L/10)*Pt
        Pr = 10*math.log10(Pr) + 30
        print(f"Attenuation {L:0.2f}dB")
        print(f"Transmitting power {Pt:0.2f}dBm, Received power {Pr:0.2f}dBm")
        T = 290 # Kelvin
        k = 1.38e-23 # Boltzmann constant
        B = 10e6 # 10MHz
        N = 10*math.log10(T*k*B) + 30
        print(f"Noise due to temperature: {N:0.4f}dBm")
        SNR = Pr / N
        print(f"SNR: {SNR:0.4f}")
        q0 = 0.1587 # 1/2 erfc(1/sqrt(2))
        qc = 4.1327 # sqrt(2*e*pi)
        BER = (q0 - (SNR-1)/qc + (SNR-1)**2/(2*qc)) / 100
        print(f"BER: {BER:0.4f}")

        bits = "".join([f"{byte:08b}" for byte in data])
        flipped_bits = []
        for i, bit in enumerate(bits):
            if random.random() < BER:
                bit = '1' if bit == '0' else '0' # Flip the bit
                print(f"flipped bit {i}")
            flipped_bits.append(bit)
        flipped_data = bytes(int("".join(flipped_bits[i:i+8]), base=2) for i in range(0, len(flipped_bits), 8))

        return flipped_data


    def send_status_update(self):
        """Send turbine status to the closest available satellite using HTTP"""
        self.update_nearest_satellite()
        if self.next_satellite is None:
            print("No satellites online. No message sent...")
            return
        turbine_data = self.generate_turbine_data()

        encrypted_data = self.encrypt_turbine_data(turbine_data)
        error_correct_data = self.hamming_encode_message(encrypted_data)
        noisy_data = self.simulate_noise(error_correct_data)

        headers = {
            'X-Destination-ID': str(self.gs_id)
        }

        time.sleep(self.simulate_leo_delay())
        # Send HTTP POST request to the next satellite
        url = f"http://{self.next_satellite[0]}:{self.next_satellite[1]}/"
        try:

            response = requests.post(url, headers=headers, data=noisy_data, verify=False, timeout=1, proxies={"http": None, "https": None})
            
            print("\033[92mStatus Update Sent:\033[0m", turbine_data, "to", self.next_satellite)

            time.sleep(self.simulate_leo_delay())
            print(response.headers)
            print("\033[91mResponse Received:\033[0m", response.status_code, response.text)

        except Exception as e:
            print(f"Error sending status update: {e}")
            # remove satellite from routing table, it's down
            network_manager.send_down_device(self.routing_table, self.shortest_path[1],self.wf_id)
            if self.shortest_path[1] in self.routing_table:
                del self.routing_table[int(self.shortest_path[1])]
                print(f"Removed satellite {self.shortest_path[1]} from routing table")
            self.send_status_update()



    def start_flask_app(self):
        threading.Thread(target=self.app.run, kwargs={
            "host": self.wf_host[0],
            "port": self.wf_host[1],
            "use_reloader": False,
            "debug": False
        }, daemon=True).start()


if __name__ == "__main__":
    try:
        turbine = WindTurbineNode()
        turbine.start_flask_app()

        input("\n"+"-"*30+"\nWind Turbine Online. Press any key to start...\n"+"-"*30+"\n\n")

        while True:
            turbine.send_status_update()
            time.sleep(5)

    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)