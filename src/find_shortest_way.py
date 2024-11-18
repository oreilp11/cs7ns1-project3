import csv
import heapq
import math
from math import radians, cos, sin, asin, sqrt, pi, erfc

def calculate_link_quality(distance):
    # Constants (using reasonable approximations)
    f = 30e9  # frequency (30 GHz) [Ka band used by Starlink]
    c = 3e8    # speed of light
    Pt = 50   # transmit power (50W) [50W used by Starlink to overcome high attenuation wrt distance]
    T = 290    # temperature (K) [Average temperature in thermosphere (85km - 690km) at LEO orbit (approx 550km) is roughly 290K]
    k = 1.38e-23  # Boltzmann constant
    B = 10e6   # bandwidth (10 MHz) [large bandwith used by Starlink for high speed internet]

    # Path loss calculation (in dB)
    L = 20 * math.log10((4 * pi * distance * 1000 * f) / c)  # distance converted to meters
    Pt = 10 * math.log10(Pt) + 30 # converting to dBm
    # Received power
    Pr = Pt * (10 ** (-L/10)) 
    Pr = 10 * math.log10(Pr) + 30 # converting to dBm
    N = 10 * math.log10(T * k * B) + 30 # converting to dBm

    # SNR calculation
    SNR = Pr / N

    # Approximate BER (using second order taylor series expansion around x=1 as erfc might be computationally expensive)
    # Higher value means better quality
    q0 = 0.1587 # 1/2 erfc(1/sqrt(2))
    qc = 4.1327 # sqrt(2*e*pi)
    quality = 1 / (q0 - (SNR-1)/qc + (SNR-1)**2/(2*qc)) # take inverse of approximated BER => higher quality = lower BER

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
            dist = haversine_alt_dist(positions[path[0]], positions[path[1]])
            return [int(node) for node in path], dist
        visited.add(node)
        for neighbor, weight in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (cost + weight, neighbor, path))

    # no viable path
    return None, None