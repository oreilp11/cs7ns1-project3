# Codebase for CS7NS1 - Project 3

Group Number: 8

Group Members:

- Paul O'Reilly \[ID - 24351186\]
- Daya Lokesh Duddupudi \[ID - 24351819\]
- Emile Delmas \[ID - 24332748\]
- Arnav Tripathy \[ID - 24332768\]

## Wind Farm, Ground Station, and Satellite Network

This project simulates a network of wind turbines, ground stations, and satellites. The wind turbines send status updates to the nearest satellite, which then forwards the data to the ground station.

### Running the Simulation

#### Using `run_simulation.sh`

1. __Run the entire simulation__:

    ```sh
    ./run_simulation.sh
    ```

    This script will start the ground station, all satellites (from 1 to 10), and the wind farm. It will also handle cleanup on termination.

#### Running Each Component Individually

1. __Run the ground station__:

    ```sh
    python src/ground_station.py
    ```

2. __Run a satellite__:

    ```sh
    python src/satellite.py <Satellite ID>
    ```

    Replace `<Satellite ID>` with an integer from 1 to 10.

3. __Run the wind farm__:

    ```sh
    python src/wind_farm.py
    ```

### Visualization

1. __Run the visualization server__:

    ```sh
    python src/visualization.py
    ```

2. __Access the visualization__:

    Open your web browser and navigate to `http://localhost:5000`.

### Project Structure

- `wind_farm.py`: Simulates wind turbines sending status updates.
- `ground_station.py`: Simulates a ground station receiving data from satellites.
- `satellite.py`: Simulates satellites forwarding data between wind turbines and the ground station.
- `visualization.py`: Provides a web interface to visualize the positions of satellites, the wind farm, and the ground station.
- `update_satellite_positions.py`: Contains functions to calculate and update satellite positions.
- `network_manager.py`: Manages network operations, including scanning for active devices and handling device down notifications.
- `find_shortest_way.py`: Implements the algorithm to find the shortest path between devices in the network.
- `wind_turbine_calculator.py`: Contains the logic to calculate wind turbine power output based on weather conditions.
- `run_simulation.sh`: Bash script to run the entire simulation, including the ground station, satellites, and wind farm.

### Protocol Structure

Uses HTTP 1.1 as a base, composed of two endpoints as follows:

#### Endpoint 1: Check if Device is Online

```http
GET / HTTP/1.1
```

No headers necessary, optional/custom headers are permitted

Returns the following JSON:

```json
{
    "device-type": 0,
    "device-id": 0,
    "group-id": 8
}
```

The following is a breakdown of the three valid codes for `device-type`:

- 0: Wind Farm Node
- 1: Satellite Node
- 2: Ground Station Node

`group-id` should be the id of your group.

`device-id` should be unique in the network of your group's devices, no need for it to be globally unique within all groups using this protocol as `group-id` can be used to resolve conflicts.

#### Endpoint 2: Remove Device from Routing Table

```http
GET /down HTTP/1.1
```

No headers necessary, optional/custom headers are permitted

Returns the following JSON:

```json
{
    "message": "Device <device-id> removed from routing table"
}
```

`message` content is not required to be in any specific format, optional fields are permitted.

#### Endpoint 3: Forward Data Through the Network

```http
POST / HTTP/1.1
```

Headers:

- `X-Destination-ID`: The ID of the destination device.
- `X-Destination-IP`: The IP address of the destination device.
- `X-Destination-Port`: The port of the destination device.
- `X-Group-ID`: The group ID.

Payload is sent in the body of this request.

Returns the following JSON:

```json
{
    "message": "Satellite <satellite-id> received data"
}
```

`message` content is not required to be in any specific format, optional fields are permitted.
