#!/bin/bash

# Démarrer tous les fichiers de configuration gNB
for gnb_cfg in ./config/gnb/*.yaml; do
  echo "Starting gNB with config: $gnb_cfg"
  ./nr-gnb -c "$gnb_cfg" &
done

# Démarrer tous les fichiers de configuration UE
for ue_cfg in ./config/ue/*.yaml; do
  echo "Starting UE with config: $ue_cfg"
  ./nr-ue -c "$ue_cfg" &
done

# Garder le conteneur actif
wait