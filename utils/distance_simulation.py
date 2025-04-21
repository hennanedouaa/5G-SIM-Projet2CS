#!/usr/bin/env python3
import sys
import logging
import time
import os
import re
from math import radians, sin, cos, sqrt, atan2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points (in km)"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1-a))

def calculate_bandwidth(distance_km):
    """Calculate bandwidth based on distance with fiber attenuation model"""
    L0 = 0.2  # Initial signal loss at 1 km (in dB)
    alpha = 0.2  # Attenuation coefficient (in dB/km)
    initial_bandwidth = 1e9  # Initial bandwidth (1 GHz)

    # Calculate the signal loss based on distance
    signal_loss = L0 * (10 ** (alpha * distance_km / 10))

    # Calculate the estimated bandwidth after attenuation
    bandwidth = initial_bandwidth / signal_loss
    return max(bandwidth / 1e6, 10)  # Convert to Mbps and ensure minimum of 10 Mbps

def get_ueransim_coords_from_docker_compose():
    """Extract UE-RANSIM coordinates from docker-compose-ulcl.yaml file"""
    compose_file = "docker-compose-ulcl.yaml"
    if not os.path.isfile(compose_file):
        logging.error(f"Error: {compose_file} not found in current directory.")
        sys.exit(1)
    
    try:
        with open(compose_file, 'r') as file:
            lines = file.readlines()
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        sys.exit(1)
    
    # Variables for UERANSIM coordinates
    ueransim_lat = None
    ueransim_lon = None
    
    in_ueransim = False
    
    for line in lines:
        line = line.strip()
        
        # Detect which section we're in
        if "free5gc-ueransim:" in line or "ueransim:" in line:
            in_ueransim = True
        elif line.startswith("free5gc-") or line.startswith("networks:"):
            in_ueransim = False
        
        # Extract coordinates based on section
        if in_ueransim:
            if "LATITUDE:" in line:
                ueransim_lat = line.split(":", 1)[1].strip()
            elif "LONGITUDE:" in line:
                ueransim_lon = line.split(":", 1)[1].strip()
            elif "location:" in line:
                # Extract coordinates from format like location: "45.7640,4.8357"
                loc_match = re.search(r'location:\s*"?([^,"]+),([^"]+)"?', line)
                if loc_match:
                    if not ueransim_lat:
                        ueransim_lat = loc_match.group(1)
                    if not ueransim_lon:
                        ueransim_lon = loc_match.group(2)
    
    if not ueransim_lat or not ueransim_lon:
        logging.error("UERANSIM coordinates not found in docker-compose file.")
        # Use default coordinates if not found
        ueransim_lat = "0.0"
        ueransim_lon = "0.0"
        logging.info(f"Using default UERANSIM coordinates: {ueransim_lat}, {ueransim_lon}")
    
    return float(ueransim_lat), float(ueransim_lon)

def get_network_interface(container):
    """Safely determine the network interface"""
    for iface in ['gtp0', 'upfgtp', 'eth0', 'eth1']:
        result = container.exec_run(f"ip link show {iface}", privileged=True)
        if result.exit_code == 0:
            return iface
    result = container.exec_run("ip route | awk '/default/ {print $5}'", privileged=True)
    return result.output.decode().strip() or 'eth0'

def clear_existing_rules(container, iface):
    """Forcefully clear all existing tc rules with lock handling"""
    cmds = [
        # First try normal deletion
        f"tc qdisc del dev {iface} root 2>/dev/null",
        # Then try deleting with force flag
        f"tc qdisc del dev {iface} root 2>/dev/null || true",
        # Finally ensure basic qdisc exists
        f"tc qdisc replace dev {iface} root pfifo_fast"
    ]
    
    for cmd in cmds:
        result = container.exec_run(cmd, privileged=True)
        time.sleep(1)  # Crucial delay to allow lock release
        if result.exit_code == 0:
            return True
    return False

def apply_bandwidth_limit(container, iface, bw):
    """Apply bandwidth limit with exclusive lock handling"""
    max_retries = 5
    latency_ms = 10  # 10ms as requested
    
    for attempt in range(1, max_retries + 1):
        try:
            # 1. First ensure basic qdisc exists (releases any locks)
            container.exec_run(
                f"tc qdisc replace dev {iface} root pfifo_fast",
                privileged=True
            )
            time.sleep(1)  # Allow lock release
            
            # 2. Calculate burst in KB (more compatible units)
            bw_kbits = bw * 1000
            burst_kb = int((bw_kbits * latency_ms) / (8 * 1000))
            
            # 3. Build and execute TC command
            cmd = (
                f"tc qdisc replace dev {iface} root tbf "
                f"rate {bw}mbit burst {burst_kb}Kb latency {latency_ms}ms"
            )
            logging.info(f"Attempt {attempt}: {cmd}")
            
            result = container.exec_run(cmd, privileged=True)
            
            if result.exit_code == 0:
                return True
                
            # Handle specific errors
            output = result.output.decode()
            if "Exclusivity flag on" in output:
                logging.warning(f"TC locked (attempt {attempt}), waiting...")
                time.sleep(attempt * 2)  # Exponential backoff
                continue
                
            raise RuntimeError(output)
            
        except Exception as e:
            logging.error(f"Attempt {attempt} failed: {str(e)}")
            if attempt == max_retries:
                raise RuntimeError(f"Failed after {max_retries} attempts: {str(e)}")
            time.sleep(attempt * 2)

def prompt_for_coordinates(ueransim_lat, ueransim_lon):
    """Prompt user for i-upf and psa-upf coordinates"""
    print("UE-RANSIM coordinates (from docker-compose-ulcl.yaml):")
    print(f"  Latitude: {ueransim_lat}")
    print(f"  Longitude: {ueransim_lon}")
    print("")
    
    print("Veuillez entrer les coordonnées pour i-upf:")
    i_lat = input("  Latitude: ")
    i_lon = input("  Longitude: ")
    
    print("\nVeuillez entrer les coordonnées pour psa-upf:")
    p_lat = input("  Latitude: ")
    p_lon = input("  Longitude: ")
    
    # Validate and convert inputs
    try:
        i_lat = float(i_lat)
        i_lon = float(i_lon)
        p_lat = float(p_lat)
        p_lon = float(p_lon)
    except ValueError:
        logging.error("Les coordonnées doivent être des nombres.")
        sys.exit(1)
    
    return i_lat, i_lon, p_lat, p_lon

def main():
    try:
        # Import docker module at the beginning
        try:
            import docker
        except ImportError:
            logging.error("Install docker SDK: pip3 install docker")
            sys.exit(1)
            
        # Get UERANSIM coordinates from docker-compose file
        ueransim_lat, ueransim_lon = get_ueransim_coords_from_docker_compose()
        
        # Prompt user for i-upf and psa-upf coordinates
        i_upf_lat, i_upf_lon, psa_upf_lat, psa_upf_lon = prompt_for_coordinates(
            ueransim_lat, ueransim_lon
        )
        
        # Calculate distances
        distance_ue_upfi = haversine(ueransim_lat, ueransim_lon, i_upf_lat, i_upf_lon)
        distance_upfi_psa = haversine(i_upf_lat, i_upf_lon, psa_upf_lat, psa_upf_lon)
        
        # Calculate bandwidths
        bw_ue_upfi = calculate_bandwidth(distance_ue_upfi)
        bw_upfi_psa = calculate_bandwidth(distance_upfi_psa)
        
        # Display results
        print("\nRésultats calculés:")
        print(f"Distance ueransim → i-upf: {distance_ue_upfi:.2f} km")
        print(f"Bande passante estimée: {bw_ue_upfi:.2f} Mbps")
        print(f"Distance i-upf → psa-upf: {distance_upfi_psa:.2f} km")
        print(f"Bande passante estimée: {bw_upfi_psa:.2f} Mbps")
        
        # Now always apply bandwidth limitations without asking
        print("\nApplication des limitations de bande passante aux conteneurs...")
                
        client = docker.from_env()
        
        try:
            # Get containers
            ueransim = client.containers.get("ueransim")
            upf_i = client.containers.get("i-upf")
            upf_psa = client.containers.get("psa-upf")
            
            # Set network interfaces
            i_upf_iface = "upfgtp"
            psa_upf_iface = "upfgtp"
            
            # Apply bandwidth limitations
            # ue - i-upf
            apply_bandwidth_limit(upf_i, i_upf_iface, bw_ue_upfi)
            logging.info(f"Limitation entre ueransim → i-upf : {distance_ue_upfi:.1f}km, {bw_ue_upfi:.2f} Mbps")
            
            # i-upf -- psa-upf
            apply_bandwidth_limit(upf_psa, psa_upf_iface, bw_upfi_psa)
            logging.info(f"Limitation entre i-upf → psa-upf : {distance_upfi_psa:.1f}km, {bw_upfi_psa:.2f} Mbps")
            
            print("\nLimitations de bande passante appliquées avec succès!")
            
        except Exception as e:
            logging.error(f"Erreur lors de l'application des limitations: {str(e)}")
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()