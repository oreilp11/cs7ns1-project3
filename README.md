# Codebase for CS7NS1 - Project 3

Group Number: 8

Group Members:

- Paul O'Reilly \[ID - 24351186\]
- Daya Lokesh Duddupudi \[ID - 24351819\]
- Emile Delmas \[ID - 24332748\]
- Arnav Tripathy \[ID - 24XXXXXX\]

## Wind Farm, Ground Station, and Satellite Network

This project simulates a network of wind turbines, ground stations, and satellites. The wind turbines send status updates to the nearest satellite, which then forwards the data to the ground station.

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
    "group-id": 0,
    "latitude": 0.0,
    "longitude": 0.0,
    "altitude": 0.0,
}
```

The following is a breakdown of the three valid codes for `device-type`:

- 0: Data Collection Node
- 1: Satellite Node
- 2: End Station Node

`group-id` should be the id of your group.

`device-id` should be unique in the network of your group's devices, no need for it to be globally unique within all groups using this protocol as `group-id` can be used to resolve conflicts

If not dynamically updating satellite position, set `latitude` & `longitude` to be a random real location reasonably close in proximity to your end station (ideally not too far from Ireland/UK but this will be usecase dependant). Set `altitude` to be somewhat realistic for the LEO context

#### Endpoint 2: Forward Data Through the Network

```http
POST / HTTP/1.1
```

No headers necessary, optional/custom headers are permitted
payload is sent in the body of this request

Returns the following JSON:

```json
{
    "message": "",
}
```

`message` content is not required to be in any specific format
optional fields are permitted

### Project Structure

- wind_farm.py : Simulates wind turbines sending status updates.
- ground_station.py : Simulates a ground station receiving data from satellites.
- satellite.py : Simulates satellites forwarding data between wind turbines and the ground station.

### Running the Simulation

#### Ground Station

 1. __Run the ground station__:

    ```sh
    python src/ground_station.py
    ```

#### Satellite

1. __Run a satellite__:

    ```sh
    python src/satellite.py <Satellite ID>
    ```

    with `<Satellite ID>` being an integer from 1 to 10.

#### Wind Farm

1. __Run the wind farm__:

    ```sh
    python src/wind_farm.py
    ```

### How Requests are Sent

#### Wind Turbine to Satellite

Wind turbines generate status updates and send them to the nearest satellite using HTTP GET requests. The headers include information such as:
- Group ID
- Destination IP
- Destination Port

#### Satellite to Ground Station

Satellites receive data from wind turbines, add a simulated delay, and forward the data to the next device (either another satellite or the ground station) using HTTP GET requests.

### Notes

- Ensure that the `devices_ip.csv` and `distances_common.csv` files are correctly set up in the `assets` directory.
- The simulation runs indefinitely until manually stopped.
