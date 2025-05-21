#!/usr/bin/env python3
import argparse
from utils.distance import apply_distance
from utils.insert import (login, insert_ue)
from utils.generate_upf_configs import (
    generate_upf_config,
    generate_docker_compose,
    generate_smf_config,
    generate_uerouting_config
)
import os
import yaml
import subprocess
import time
import docker
from datetime import datetime
import sys



def generate_ue_configs(total_ues):
    # Chemins des répertoires
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(scripts_dir, 'config/custom/ue')

    # Vérifier si le répertoire existe
    if not os.path.exists(config_dir):
        print(f"Le répertoire {config_dir} n'existe pas!")
        return

    # Lister les fichiers UE existants
    existing_ues = [f for f in os.listdir(config_dir)
                   if f.startswith('uecfg') and f.endswith('.yaml')]
    existing_count = len(existing_ues)

    # Vérifier si on a déjà assez de fichiers
    if existing_count >= total_ues:
        print(f"Il existe déjà {existing_count} fichiers UE (le total demandé est {total_ues})")
        return

    # Tenant ID (peut être personnalisé)
    tenant_id = "6b8d30f1-c2a4-47e3-989b-72511aef87d8"

    # Charger le modèle de configuration
    template_path = os.path.join(config_dir, 'uecfg1.yaml')
    if not os.path.exists(template_path):
        print(f"Le fichier modèle {template_path} n'existe pas!")
        return

    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)

    # Générer les nouveaux fichiers
    for i in range(existing_count + 1, total_ues + 1):

        # Générer le nom du fichier
        new_filename = f"uecfg{i}.yaml"
        new_filepath = os.path.join(config_dir, new_filename)

        # Écrire le nouveau fichier
        with open(new_filepath, 'w') as f:
            yaml.dump(template, f, sort_keys=False)

        print(f"Créé {new_filename}")

        # Générer et exécuter les commandes MongoDB
        insert_ue(i)
        print(f"Données MongoDB insérées pour ue {i}")

def check_upf_containers_running(num_upfs, timeout=60):
    """Check if all UPF containers are running"""
    client = docker.from_env()
    expected_upfs = num_upfs  # includes all UPFs (intermediate + PSA)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        running_upfs = 0
        try:
            containers = client.containers.list()
            for container in containers:
                if 'upf' in container.name.lower():
                    if container.status == 'running':
                        running_upfs += 1
            if running_upfs >= expected_upfs:
                return True
        except Exception as e:
            print(f"Error checking containers: {e}")
        
        time.sleep(5)
        print(f"Waiting for UPF containers to start... ({running_upfs}/{expected_upfs} running)")
    
    return False
    
def connect_ues():
    """Executes nr-ue inside the UERANSIM container for each UE config file"""
    try:
        client = docker.from_env()
        container = next((c for c in client.containers.list() if 'ueransim' in c.name.lower()), None)

        if not container:
            print("UERANSIM container not running.")
            return

        ue_config_dir = "./config/custom/ue"
        ue_files = sorted(f for f in os.listdir(ue_config_dir) if f.startswith("uecfg") and f.endswith(".yaml"))

        if not ue_files:
            print("No UE config files found.")
            return

        for file in ue_files:
            cmd = f"./nr-ue -c /ueransim/config/ue/{file}"
            print(f"Executing in container: {cmd}")
            exec_result = container.exec_run(cmd, detach=True, workdir="/ueransim")
            print(f"Started UE with config {file}, Exec ID: {exec_result}")

        print("All UEs launched.")
    except docker.errors.DockerException as e:
        print(f"Error executing UE commands in UERANSIM: {e}")


def main():
    """Main function to parse arguments and generate configuration files"""
    parser = argparse.ArgumentParser(description="Generate Free5GC configuration files")
    
    # UPF topology arguments
    parser.add_argument("--num_upfs", type=int, help="Total number of UPFs (including PSA-UPF)")
    parser.add_argument("--edge_upfs", type=int, default=1, help="Number of edge UPFs with N3 interfaces")
    
    # UE configuration arguments
    parser.add_argument("--ue", type=int, help="Number of UE config files to generate")

    args = parser.parse_args()

    # Handle UPF topology generation if num_upfs is provided
    if args.num_upfs is not None:
        handle_topology_generation(args)

    # Handle UE generation if ue is provided
    if args.ue is not None:
        handle_ue_generation(args)

    # If no arguments provided, show help
    if args.num_upfs is None and args.ue is None:
        parser.print_help()

def handle_topology_generation(args):
    """Handle the topology generation"""
    # Validate arguments
    if args.num_upfs < 2:
        raise ValueError("Number of UPFs must be at least 2 (one PSA-UPF and at least one intermediate UPF)")

    if args.edge_upfs < 1 or args.edge_upfs >= args.num_upfs:
        raise ValueError("Number of edge UPFs must be at least 1 and less than total UPFs")

    # Set up config output directory
    
    custom_config_dir = "./config/custom"
    os.makedirs(custom_config_dir, exist_ok=True)

    # Generate UPF configuration files
    for i in range(1, args.num_upfs):
        hostname = f"i-upf{i}" if i > 1 else "i-upf"
        is_edge = i <= args.edge_upfs
        upf_config = generate_upf_config(hostname, is_edge=is_edge)

        with open(os.path.join(custom_config_dir, f"upfcfg-{hostname}.yaml"), "w") as f:
            yaml.dump(upf_config, f, default_flow_style=False)

    # Generate PSA-UPF configuration
    psa_config = generate_upf_config("remote-surgery", is_psa=True)
    with open(os.path.join(custom_config_dir, "upfcfg-psa-upf.yaml"), "w") as f:
        yaml.dump(psa_config, f, default_flow_style=False)

    # Generate SMF configuration
    smf_config = generate_smf_config(args.num_upfs, args.edge_upfs)
    with open(os.path.join(custom_config_dir, "smfcfg.yaml"), "w") as f:
        yaml.dump(smf_config, f, default_flow_style=False)

    # Generate UE routing configuration
    uerouting_config = generate_uerouting_config(args.num_upfs, args.edge_upfs)
    with open(os.path.join(custom_config_dir, "uerouting.yaml"), "w") as f:
        yaml.dump(uerouting_config, f, default_flow_style=False)

    # Generate Docker Compose configuration in the current directory
    docker_compose = generate_docker_compose(args.num_upfs, args.edge_upfs)
    with open("docker-compose-custom.yaml", "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False)

    print(f"Configuration files generated:")
    print(f"- {args.num_upfs - 1} intermediate UPF configs in {custom_config_dir}")
    print(f"- 1 PSA UPF config in {custom_config_dir}")
    print(f"- SMF config with UPF topology in {custom_config_dir}")
    print(f"- UE routing config in {custom_config_dir}")
    print(f"- Docker Compose file: ./docker-compose-custom.yaml")

    # Start the containers
    print("\nStarting containers with docker-compose...")
    try:
        subprocess.run(["docker", "compose", "-f", "docker-compose-custom.yaml", "up", "-d"], check=True)
        print("Containers started in detached mode")
    except subprocess.CalledProcessError as e:
        print(f"Failed to start containers: {e}")
        return

    # Wait for UPF containers to start
    print("\nWaiting for all UPF containers to start...")
    #if not check_upf_containers_running(args.num_upfs):
     #   print("Timeout waiting for UPF containers to start")
      #  return
    #print("All UPF containers are running")

    # Prompt for coordinates and apply distance-based shaping
    print("\nNow, enter the geographic coordinates (x, y) for each UPF (in decimal degrees):")
    upf_coords = {}
    for i in range(1, args.num_upfs):
        name = f"i-upf{i}" if i > 1 else "i-upf"
        x = float(input(f"Enter x (latitude) for {name}: "))
        y = float(input(f"Enter y (longitude) for {name}: "))
        upf_coords[name] = {"x": x, "y": y}

    # PSA-UPF
    x = float(input("Enter x (latitude) for psa-upf: "))
    y = float(input("Enter y (longitude) for psa-upf: "))
    upf_coords["psa-upf"] = {"x": x, "y": y}

    print("\nApplying distance-based bandwidth limits using tc...")
    #apply_distance(upf_coords)
    #print("Bandwidth shaping complete.")

def handle_ue_generation(args):
    if args.ue <= 0:
        print("Number of UEs must be greater than 0.")
        exit(1)

    generate_ue_configs(args.ue)

    try:
        client = docker.from_env()
        ueransim_container = next(
            (c for c in client.containers.list(all=True) if 'ueransim' in c.name.lower()), None)

        if ueransim_container:
            print(f"Redémarrage du conteneur {ueransim_container.name}...")
            ueransim_container.restart()
            print("UERANSIM redémarré avec succès.")
            time.sleep(5)  # Give it time to fully restart
            connect_ues()  # <-- Launch UEs inside the container
        else:
            print("Conteneur UERANSIM introuvable.")
    except docker.errors.DockerException as e:
        print(f"Erreur lors du redémarrage de UERANSIM : {e}")

    print(f"Generated {args.ue} UE configuration files")


if __name__ == "__main__":
   
    main()

