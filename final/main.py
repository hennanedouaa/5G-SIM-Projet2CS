#!/usr/bin/env python3
import argparse
from utils.distance import apply_distance
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

def main():
    """Main function to parse arguments and generate configuration files"""
    parser = argparse.ArgumentParser(description="Generate Free5GC UPF topology configuration")
    parser.add_argument("--num_upfs", type=int, required=True, help="Total number of UPFs (including PSA-UPF)")
    parser.add_argument("--edge_upfs", type=int, default=1, help="Number of edge UPFs with N3 interfaces")

    args = parser.parse_args()

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

    # === NEW SECTION: Prompt for coordinates and apply distance-based shaping ===
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

if __name__ == "__main__":
    main()
