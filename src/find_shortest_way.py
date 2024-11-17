import csv
import heapq
import math
from math import radians, cos, sin, asin, sqrt, pi, erfc

def calculate_link_quality(distance):
    # Constants (using reasonable approximations)
    f = 2.4e9  # frequency (2.4 GHz)
    c = 3e8    # speed of light
    Pt = 0.1   # transmit power (100mW)
    T = 290    # temperature (K)
    k = 1.38e-23  # Boltzmann constant
    B = 20e6   # bandwidth (20 MHz)

    # Path loss calculation (in dB)
    L = 20 * math.log10((4 * pi * distance * 1000 * f) / c)  # distance converted to meters

    # Received power
    Pr = Pt * (10 ** (-L/10))

    # SNR calculation
    SNR = Pr / (T * k * B)

    # Approximate BER (using simplified calculation as erfc might be computationally expensive)
    # We'll use log(1 + SNR) as a quality metric instead of actual BER
    # Higher value means better quality
    quality = math.log(1 + SNR)

    return quality

def haversine(lon1, lat1, lon2, lat2):
    # Convert coordinates to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers
    r = 6371
    return c * r

def find_shortest_path(positions_list, start_node, end_node, broken_devices=None):
    if broken_devices is None:
        broken_devices = set()
    else:
        broken_devices = set(broken_devices)

    if start_node in broken_devices or end_node in broken_devices:
        print("Error: Start or end node is in broken devices list")
        return

    # Convert positions list to dictionary
    positions = {str(pos['id']): pos for pos in positions_list}

    graph = {}
    # Build graph based on positions and rules
    for dev1 in positions:
        for dev2 in positions:
            if dev1 != dev2 and dev1 not in broken_devices and dev2 not in broken_devices:
                pos1 = positions[dev1]
                pos2 = positions[dev2]
                distance = haversine(pos1['long'], pos1['lat'], pos2['long'], pos2['lat'])

                # Apply connection rules
                can_connect = True
                # Rule 1: 0 & -1 can't connect directly
                if (dev1 in ['-1', '0'] and dev2 in ['-1', '0']):
                    can_connect = False


                if can_connect:
                    # Calculate link quality and use it to modify the weight
                    link_quality = calculate_link_quality(distance)
                    # Weight is now a combination of distance and signal quality
                    # We use distance/link_quality so that:
                    # - Higher distances increase the weight
                    # - Better signal quality decreases the weight
                    weight = distance / link_quality

                    graph.setdefault(dev1, []).append((dev2, weight))
                    graph.setdefault(dev2, []).append((dev1, weight))

    # Rest of the pathfinding algorithm remains the same
    queue = [(0, str(start_node), [])]
    visited = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in visited:
            continue
        path = path + [node]
        if node == str(end_node):
            print(f"Shortest distance: {cost:0.3f} km")
            print("Path:", " -> ".join(path))
            return [int(node) for node in path], cost
        visited.add(node)
        for neighbor, weight in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (cost + weight, neighbor, path))

    # no viable path
    return None, None