# Codebase for CS7NS1 - Project 3
Group Number: 8

__Group Members__
- Paul O'Reilly \[ID - 24351186\]
- Daya Lokesh Duddupudi \[ID - 24351819\]
- Emile Delmas \[ID - 24332748\]
- Arnav Tripathy \[ID - 24XXXXXX\]

## Wind Farm, Ground Station, and Satellite Network

This project simulates a network of wind turbines, ground stations, and satellites. The wind turbines send status updates to the nearest satellite, which then forwards the data to the ground station.

### Project Structure

- wind_farm.py : Simulates wind turbines sending status updates.
- ground_station.py : Simulates a ground station receiving data from satellites.
- satellite.py : Simulates satellites forwarding data between wind turbines and the ground station.

### Running the Simulation

#### Ground Station


 1. **Run the ground station**:
    ```sh
    python src/ground_station.py
    ```

#### Satellite

1. **Run a satellite**:
    ```sh
    python src/satellite.py <Satellite ID>
    ```

    with `<Satellite ID>` being an integer from 1 to 5.

#### Wind Farm

1. **Run the wind farm**:
    ```sh
    python src/wind_farm.py
    ```

### How Requests are Sent

#### Wind Turbine to Satellite

Wind turbines generate status updates and send them to the nearest satellite using HTTP GET requests. The headers include custom Bobb headers for protocol information.

#### Satellite to Ground Station

Satellites receive data from wind turbines, add a simulated delay, and forward the data to the next device (either another satellite or the ground station) using HTTP GET requests.

### Example Request

**Wind Turbine to Satellite**:
```plaintext
GET / HTTP/1.1
Host: <Satellite IP>:<Satellite Port>
X-Bobb-Header: <hexadecimal Bobb header>
X-Bobb-Optional-Header: <hexadecimal Bobb optional header>
```

**Satellite to Ground Station**:
```plaintext
GET / HTTP/1.1
Host: <Ground Station IP>:<Ground Station Port>
X-Bobb-Header: <hexadecimal Bobb header>
X-Bobb-Optional-Header: <hexadecimal Bobb optional header>
```

### Custom Headers

- **X-Bobb-Header**: Contains protocol information such as version, message type, source and destination IPs and ports, sequence number, and timestamp.
- **X-Bobb-Optional-Header**: Contains optional information such as timestamp, hop count, priority, and encryption algorithm.

### Example Response

**Ground Station Response**:
```json
{
  "message": "Data received at Ground Station"
}
```

### Notes

- Ensure that the `devices_ip.csv` and `distances_common.csv` files are correctly set up in the `assets` directory.
- The simulation runs indefinitely until manually stopped.
