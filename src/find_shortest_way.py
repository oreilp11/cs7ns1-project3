import csv
import heapq
import math
from math import radians, cos, sin, asin, sqrt, pi, erfc

def calculate_link_quality(distance, is_ground_transmission=False):
    # Constants (using reasonable approximations)
    f = 2.4e8 # frequency (2.4GHz)
    C = 3e8 # speed of light [m/s^2]
    Pt = 50 # transmit power [50W used by Starlink to overcome high attenuation wrt distance]
    Pr = Pt * (C/(4 * math.pi * distance * 1000 * f))**2 # receiver power using FSPL model
    Pt = 10*math.log10(Pt) + 30
    Pr = 10*math.log10(Pr) + 30
    T = 290 # temperature (K) [Average temperature in thermosphere (85km - 690km) at LEO orbit (approx 550km) is roughly 290K]
    k = 1.38e-23 # Boltzmann constant
    B = 10e6 # bandwidth (10 MHz)
    Nt = 10*math.log10(T*k*B) + 30 # AWGN for ambient temperature at receiver
    sigma = 1e-8 if is_ground_transmission else 1e-9 # Coeficient for transit time noise, influenced by atmospheric conditions
    Nphi = 10*math.log10(1+(2*math.pi*f*sigma)) # Transit time noise
    SNR = Pr - (Nt + Nphi) # Signal to Noise Ratio
    quality = 2 / max(math.erfc(SNR/math.sqrt(2)), 1e-100) # Inverse of Bit Error Rate, formula valid for BPKS/QPKS modulation

    return quality


def haversine_alt_dist(pos1, pos2):
    # Convert coordinates to radians
    lon1, lat1, lon2, lat2 = map(radians, [pos1['long'], pos1['lat'], pos2['long'], pos2['lat']])
    alt1, alt2 = map(float, [pos1['alt'], pos2['alt']])
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers
    r = 6371
    haversine_dist = c * r
    true_dist = math.sqrt(haversine_dist**2 + (alt1-alt2)**2)
    return true_dist


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
                distance = haversine_alt_dist(pos1, pos2)

                # Apply connection rules
                can_connect = True
                # Rule 1: 0 & -1 can't connect directly
                if (dev1 in ['-1', '0'] and dev2 in ['-1', '0']):
                    can_connect = False


                if can_connect:
                    # Calculate link quality and use it to modify the weight
                    is_ground_transmission = dev1 in ['-1', '0'] or dev2 in ['-1', '0']
                    link_quality = calculate_link_quality(distance, is_ground_transmission)
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
            print("Path:", " -> ".join(path))
            dist = haversine_alt_dist(positions[path[0]], positions[path[1]])
            return [int(node) for node in path], dist
        visited.add(node)
        for neighbor, weight in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (cost + weight, neighbor, path))

    # no viable path
    return None, None