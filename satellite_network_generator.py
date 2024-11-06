# satellite_network_generator.py

import sys
import threading
import csv
import random
import matplotlib.pyplot as plt
import networkx as nx
import math

class Device(threading.Thread):
    def __init__(self, name, ip, device_type, port):
        super().__init__()
        self.name = name
        self.ip = ip
        self.device_type = device_type
        self.port = port

    def run(self):
        # Simulate device activity
        pass

def generate_ips(input_ips, total_devices):
    ips = []
    for i in range(total_devices):
        ip = input_ips[i % len(input_ips)]
        ips.append(ip)
    return ips

def create_devices(ips):
    devices = []
    ports = random.sample(range(1000, 65536), len(ips))
    devices.append(Device('Offshore Windfarm', ips[0], 'Windfarm', ports[0]))
    devices.append(Device('Ground Station', ips[1], 'Ground Station', ports[1]))

    for i in range(5):  # Use exactly 3 satellites
        devices.append(Device(f'Satellite {i+1}', ips[2 + i], 'Satellite', ports[2 + i]))

    return devices

def assign_positions(devices):
    device_positions = {}
    # Windfarm at (0, 0, 0)
    device_positions['Offshore Windfarm'] = (0, 0, 0)
    # Ground Station at (1000, 0, 0)
    device_positions['Ground Station'] = (1000, 0, 0)
    # Satellites evenly spaced between Windfarm and Ground Station at 550 km altitude
    num_satellites = 5
    for i in range(num_satellites):
        x = random.randint(100, 1800)
        y = 0
        z = 550 +random.randint(-50, 50)
        device_positions[f'Satellite {i+1}'] = (x, y, z)
    return device_positions

def calculate_distances(devices, device_positions, max_satellite_distance,max_isl_distane):
    distances = {}
    for i in range(len(devices)):
        for j in range(i+1, len(devices)):
            dev1 = devices[i]
            dev2 = devices[j]
            # Prevent direct communication between Windfarm and Ground Station
            if (dev1.device_type == 'Windfarm' and dev2.device_type == 'Ground Station') or \
               (dev1.device_type == 'Ground Station' and dev2.device_type == 'Windfarm'):
                continue
            pos1 = device_positions[dev1.name]
            pos2 = device_positions[dev2.name]
            # Calculate distance
            distance = math.sqrt((pos1[0] - pos2[0])**2 +
                                 (pos1[1] - pos2[1])**2 +
                                 (pos1[2] - pos2[2])**2)
            # Apply max distance for non satellite devices
            if dev1.device_type != 'Satellite' or dev2.device_type != 'Satellite':
              if distance > max_satellite_distance:
                  continue
            else:
              if distance > max_isl_distane:
                  continue
            distances[(dev1.name, dev2.name)] = distance
    return distances

def write_csv(devices, distances):
    with open('distances.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Device1', 'IP1', 'Port1', 'Device2', 'IP2', 'Port2', 'Distance_km'])
        device_dict = {device.name: device for device in devices}
        for key, value in distances.items():
            dev1, dev2 = key
            writer.writerow([
                dev1,
                device_dict[dev1].ip,
                device_dict[dev1].port,
                dev2,
                device_dict[dev2].ip,
                device_dict[dev2].port,
                value
            ])

def plot_network(devices, distances, device_positions,max_satellite_distance):
    G = nx.Graph()
    for device in devices:
        G.add_node(device.name, ip=device.ip, device_type=device.device_type,port=device.port)
    for (dev1, dev2), distance in distances.items():
        G.add_edge(dev1, dev2, weight=distance)
    pos = {device.name: (device_positions[device.name][0], device_positions[device.name][2]) for device in devices}
    labels = {node: f"{node}\n{G.nodes[node]['ip']}\n port : {G.nodes[node]['port']}" for node in G.nodes()}
    edge_labels = {(u, v): f"{d['weight']:.1f} km" for u, v, d in G.edges(data=True)}
    plt.figure(figsize=(10, 8))
    nx.draw(G, pos, with_labels=False, node_size=2000, node_color='lightblue')
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_size=7)
    plt.title("Network Diagram with IPs and Distances")
    plt.axis('off')
    plt.savefig('network_diagram.pdf')
    # plt.show()

def main():
    total_devices = 7
    input_ips = sys.argv[1:]  # Accept IPs as command-line arguments
    if len(input_ips) < 1 or len(input_ips) > 2:
        print("Please provide one or two IP addresses.")
        sys.exit(1)
    ips = generate_ips(input_ips, total_devices)
    devices = create_devices(ips)

    for device in devices:
        device.start()

    device_positions = assign_positions(devices)
    max_satellite_distance = 700  # Max distance in km
    max_isl_distane = 1000
    distances = calculate_distances(devices, device_positions, max_satellite_distance,max_isl_distane)
    write_csv(devices, distances)
    plot_network(devices, distances, device_positions, max_satellite_distance)

if __name__ == "__main__":
    main()