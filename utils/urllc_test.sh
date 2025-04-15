#!/bin/bash

# extract psa-upf address
DEST=$(cat tgt_adr)
PKT_SIZE=${1:-64}
INTERVAL=${2:-0.5}
COUNT=${3:-10}

echo "Starting test with parameters:"
echo "Destination  : $DEST"
echo "Packet size  : $PKT_SIZE"
echo "Interval     : $INTERVAL"
echo "Count        : $COUNT"

ping -s $PKT_SIZE -i $INTERVAL -c $COUNT $DEST

echo "Finished Test."
