#!/bin/bash

# psa-upf address
TGT_ADR=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' psa-upf)

echo "PSA-UPF: $TGT_ADR"

# copy urllc_test.sh inside the container to be executed
sudo docker cp ~/free5gc-compose/urllc_test.sh ueransim:/root/urllc_test.sh

# also copy psa-upf address
echo $TGT_ADR > tgt_adr
sudo docker cp tgt_adr ueransim:/root/tgt_adr
