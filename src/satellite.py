# Written by Emile Delmas, Paul O'Reilly & Arnav Tripathy
import random
import time
import threading
import math
import sys

from flask import Flask, request, jsonify
import requests

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
            print(f"Data received at Satellite {self.sat_id} : {data[:24]}")
            threading.Thread(target=self.forward_data, args=(headers, data)).start()
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


    def simulate_noise(self, data: bytes) -> bytes:
        f = 2.4e8 # frequency (2.4GHz)
        C = 3e8 # speed of light [m/s^2]
        Pt = 50 # transmit power [50W used by Starlink to overcome high attenuation wrt distance]
        Pr = Pt * (C/(4 * math.pi * self.distance * 1000 * f))**2 # receiver power using FSPL model
        Pt = 10*math.log10(Pt) + 30 # convert to dBm
        Pr = 10*math.log10(Pr) + 30 # convert to dBm
        print(f"Transmitting power {Pt:0.2f}dBm, Received power {Pr:0.2f}dBm")
        T = 290 # Kelvin
        k = 1.38e-23 # Boltzmann constant
        B = 10e6 # 10MHz
        Nt = 10*math.log10(T*k*B) + 30 # AWGN for ambient temperature at receiver
        print(f"Noise due to temperature: {Nt:0.2f}dBm")
        # Coeficient for transit time noise, influenced by atmospheric conditions
        sigma = 1e-9 # Excellent conditions in space
        Nphi = 10*math.log10(1+(2*math.pi*f*sigma)) # Transit time noise
        print(f"Noise due to transit time: {Nphi:0.2f}dBm")
        SNR = Pr - (Nt + Nphi) # Signal to Noise Ratio (dBm calculation form)
        print(f"SNR: {SNR:0.2f}")
        BER = 0.5*math.erfc(SNR/math.sqrt(2)) # Bit Error Rate, formula valid for BPKS/QPKS modulation
        print(f"BER: {BER:0.2e}")

        bits = "".join([f"{byte:08b}" for byte in data])
        flipped_bits = []
        tally = 0
        for bit in bits:
            if random.random() < BER:
                bit = '1' if bit == '0' else '0' # Flip the bit
                tally += 1
            flipped_bits.append(bit)
        flipped_data = bytes(int("".join(flipped_bits[i:i+8]), base=2) for i in range(0, len(flipped_bits), 8))
        print(f"flipped {tally} bits")

        return flipped_data


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
        current_byte = ""
        for bit_group in encoded_bits:
            current_byte += bit_group
            while len(current_byte) >= 8:
                encoded_message.append(int(current_byte[:8], 2))
                current_byte = current_byte[8:]
        if current_byte:
            encoded_message.append(int(current_byte.ljust(8, "0"), 2))
        return bytes(encoded_message)


    def forward_data(self, headers, data):

        if 'X-Destination-ID' in headers:
            print(f"\n-----\nDestination ID: {headers['X-Destination-ID']}\n-----\n")

        if headers['X-Group-ID'] == '8':
            self.update_nearest_satellite()
            # decoded_data = self.hamming_decode_message(data)
            # # check if message is corrupt (maybe implement AES if time)
            # encoded_data = self.hamming_encode_message(decoded_data)
            # data = self.simulate_noise(encoded_data)
        else:
            self.next_device = headers['X-Destination-IP'], headers['X-Destination-Port']

        if not self.next_device:
            print("No next device to forward the message.")
            return

        try:
            next_ip, next_port = self.next_device
            # Forward the HTTP request to the next device
            print(f"Forwarding data to {next_ip}:{next_port}")
            time.sleep(self.simulate_leo_delay())
            response = requests.post(f"http://{next_ip}:{next_port}/", headers=headers, data=data, verify=False,proxies={"http": None, "https": None})
            time.sleep(self.simulate_leo_delay())
            print(f"Forwarded data to {next_ip}:{next_port}, response: {response.status_code}")
        except Exception as e:
            print(f"Error forwarding data: {e}")
            network_manager.send_down_device(self.routing_table, self.shortest_path[1], self.sat_id)
            if self.shortest_path[1] in self.routing_table:
                del self.routing_table[int(self.shortest_path[1])]
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
            network_manager.scan_network(
                device_id=satellite.sat_id, 
                device_port=satellite.sat_host[1], 
                exclude_list={f"{ip}:{port}" for ip, port in satellite.routing_table.values()}
            )
            time.sleep(60)
    except KeyboardInterrupt:
        print("-"*30+"\nSimulation stopped by user\n"+"-"*30)

