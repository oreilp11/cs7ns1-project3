import requests
from typing import Dict, Tuple, List
import time
import os
import threading
import random
import update_satellite_positions

def read_ips() -> List[str]:
    """Read IPs from file"""
    try:
        # filename is in assets, ip.txt
        filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "ip.txt")
        with open(filename, 'r') as f:
            return [ip.strip() for ip in f.readlines() if ip.strip()]
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using localhost.")
        return ['0.0.0.0']

def read_other_network_satellites() -> Dict[int, Tuple[str, int]]:
  """Read other network satellites from file"""
  try:
    # filename is in assets, other_network_satellites.txt
    filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "other_satellites.txt")
    with open(filename, 'r') as f:
      lines = f.readlines()
      if not lines:
        return {}
      return {int(line.split()[0]): (line.split()[1], int(line.split()[2])) for line in lines}
  except FileNotFoundError:
    print(f"Warning: {filename} not found. Using empty dictionary.")
    return {}

def scan_network(device_id, device_port, start_port: int = 33001, end_port: int = 33010) -> Dict[int, Tuple[str, int]]:
  """
  Scan network for active devices on all IPs from ip.txt
  Returns a dictionary mapping device IDs to their (host, port) tuples
  """
  active_devices = read_other_network_satellites()
  ips = read_ips()
  print(f"Scanning network for devices on ports {start_port}-{end_port} and port 33999 on IPs: {ips}")

  device_positions = update_satellite_positions.calculate_satellite_positions(range(1, 11))
  # add yourself to the routing table
  for ip in ips:
    for port in list(range(start_port, end_port + 1)) + [33999]:
      try:
        next_id = start_port - 33000
        delay = simulate_leo_delay(device_positions,device_id,next_id)
        time.sleep(delay)
        response = requests.get(f"http://{ip}:{port}/", params={'device-id': device_id, 'device-port': device_port}, timeout=1, proxies={"http": None, "https": None})
        time.sleep(delay)
        if response.status_code == 200:
          device_info = response.json()
          found_device_id = int(device_info.get('device-id'))
          if found_device_id is not None:
            active_devices[found_device_id] = (ip, port)
            print(f"Found device {found_device_id} at {ip}:{port}")
      except requests.exceptions.RequestException:
        continue

  return active_devices

def simulate_leo_delay(device_positions,device_id,next_id) -> float:
    """Simulate LEO transmission delay with jitter"""
    distance = update_satellite_positions.haversine_distance(device_positions[device_id]['lat'], device_positions[device_id]['long'], device_positions[next_id]['lat'], device_positions[next_id]['long'])
    C = 299_792_458 / 1000.0*1000.0  # kilometres per millisecond
    base_delay = distance / C # milliseconds
    jitter = random.uniform(2, 8) # milliseconds
    leo_delay = (base_delay + jitter) / 1000 # seconds
    print(f"Adding {leo_delay:0.4f}s delay")
    return leo_delay

def send_down_device(routing_table, device_id, source_id):
  """
  Send to everyone except the device_id, that the device is down
  """
  device_positions = update_satellite_positions.calculate_satellite_positions(range(1, 11))
  def notify_device(next_device_id, next_ip, next_port):
    try:
      next_id = next_port - 33000
      delay = simulate_leo_delay(device_positions,device_id,next_id)
      time.sleep(delay)
      requests.get(f"http://{next_ip}:{next_port}/down", params={'device-id': device_id}, timeout=1, proxies={"http": None, "https": None})
      time.sleep(delay)
    except requests.exceptions.RequestException:
      print(f"Error sending down message to device {next_device_id}")

  threads = []
  # exclude the device down and source
  for next_device_id, (next_ip, next_port) in routing_table.items():
    if next_device_id == device_id or next_device_id == source_id:
      continue
    thread = threading.Thread(target=notify_device, args=(next_device_id, next_ip, next_port))
    threads.append(thread)
    thread.start()

  for thread in threads:
    thread.join()