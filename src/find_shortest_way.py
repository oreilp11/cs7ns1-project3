import csv
import os
import heapq

def find_shortest_path(start_node, end_node, broken_devices=None):
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"assets")
    print("start_node", start_node)
    if broken_devices is None:
        broken_devices = set()
    else:
        broken_devices = set(broken_devices)

    # Check if start or end nodes are broken
    if start_node in broken_devices or end_node in broken_devices:
        print("Error: Start or end node is in broken devices list")
        return

    graph = {}
    with open(os.path.join(base_path, "distances_common.csv"), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            device1 = row['id1']
            device2 = row['id2']
            distance = float(row['Distance_km'])

            # Skip connections involving broken devices
            if device1 in broken_devices or device2 in broken_devices:
                continue

            graph.setdefault(device1, []).append((device2, distance))
            # print(graph)
            graph.setdefault(device2, []).append((device1, distance))

    queue = [(0, str(start_node), [])]
    visited = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in visited:
            continue
        path = path + [node]
        if node == str(end_node):
            print(f"Shortest distance: {cost} km")
            print("Path:", " -> ".join(path))
            return [int(node) for node in path]
        visited.add(node)
        for neighbor, weight in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (cost + weight, neighbor, path))
