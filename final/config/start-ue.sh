#!/bin/bash

# Start the gNB
./nr-gnb -c ./config/gnbcfg.yaml &

# Start a UE process for each config file
for file in ./config/ue/uecfg*.yaml; do
    echo "Starting UE with config: $file"
    ./nr-ue -c "$file" &
done

# Wait for all background processes to keep the container running
wait

