#!/bin/bash

pids=()

# Function to kill all background processes
cleanup()
{
    echo "Terminating processes..."
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null
    done
    exit 0
}

trap cleanup SIGINT

# start visualization
python src/visualization.py &
pids+=($!)

# Start ground station
python src/ground_station.py &
pids+=($!)
sleep 1

# Start satellites from 1 to 10
for i in {1..10}
do
    python src/satellite.py "$i" &
    pids+=($!)
    # add some delay
    sleep 1
done

# Start wind farm
python src/wind_farm.py &
pids+=($!)



wait
