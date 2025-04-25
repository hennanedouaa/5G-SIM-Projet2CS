#!/usr/bin/env python3
import argparse
import logging
import os
import re
import sys
import time
from math import radians, sin, cos, sqrt, atan2

# Optional import if auth_ping_measure is needed
try:
    from ping_and_measure import (
        auth_ping_measure, save_results, cleanup_ue_interfaces
    )
    PING_AVAILABLE = True
except ImportError:
    PING_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1-a))

def calculate_bandwidth(distance_km):
    L0, alpha = 0.2, 0.2
    initial_bandwidth = 1e9
    signal_loss = L0 * (10 ** (alpha * distance_km / 10))
    return max(initial_bandwidth / signal_loss / 1e6, 10)

def get_ueransim_coords_from_docker_compose():
    compose_file = "docker-compose-ulcl.yaml"
    if not os.path.isfile(compose_file):
        logging.error(f"Error: {compose_file} not found.")
        sys.exit(1)
    with open(compose_file, 'r') as file:
        lines = file.readlines()

    ueransim_lat, ueransim_lon = None, None
    in_ueransim = False
    for line in lines:
        line = line.strip()
        if "ueransim:" in line:
            in_ueransim = True
        elif line.startswith("free5gc-") or line.startswith("networks:"):
            in_ueransim = False
        if in_ueransim:
            if "LATITUDE:" in line:
                ueransim_lat = line.split(":")[1].strip()
            elif "LONGITUDE:" in line:
                ueransim_lon = line.split(":")[1].strip()
            elif "location:" in line:
                match = re.search(r'location:\s*"?([^,"]+),([^"]+)"?', line)
                if match:
                    ueransim_lat, ueransim_lon = match.group(1), match.group(2)

    if not ueransim_lat or not ueransim_lon:
        logging.warning("Defaulting UERANSIM coordinates to 0.0, 0.0")
        return 0.0, 0.0
    return float(ueransim_lat), float(ueransim_lon)

def apply_bandwidth_limit(container, iface, bw):
    import docker
    max_retries, latency_ms = 5, 10
    bw_kbits = bw * 1000
    burst_kb = int((bw_kbits * latency_ms) / (8 * 1000))
    cmd = (
        f"tc qdisc replace dev {iface} root tbf "
        f"rate {bw}mbit burst {burst_kb}Kb latency {latency_ms}ms"
    )
    for attempt in range(max_retries):
        result = container.exec_run(cmd, privileged=True)
        if result.exit_code == 0:
            return True
        logging.warning(f"Attempt {attempt+1} failed. Retrying...")
        time.sleep((attempt+1)*2)
    raise RuntimeError("Bandwidth setting failed after retries.")

def main():
    parser = argparse.ArgumentParser(description="Distance and Ping Testing Tool")
    parser.add_argument('--run-ping', action='store_true', help='Run ping/auth test after bandwidth setup')
    parser.add_argument('-n', '--num_ues', type=int, default=1)
    parser.add_argument('-s', '--packet_size', type=str, default='8')
    parser.add_argument('-c', '--config_prefix', type=str, default='config/uecfg')
    parser.add_argument('-p', '--ping_count', type=int, default=5)
    parser.add_argument('-i', '--interval', type=str, default='0.02')
    parser.add_argument('-q', '--qos', type=str, default='0xb8')
    args = parser.parse_args()

    try:
        import docker
    except ImportError:
        logging.error("Install docker SDK: pip3 install docker")
        sys.exit(1)

    ueransim_lat, ueransim_lon = get_ueransim_coords_from_docker_compose()
    print("Enter i-upf coordinates:")
    i_lat = float(input("  Latitude: "))
    i_lon = float(input("  Longitude: "))
    print("Enter psa-upf coordinates:")
    p_lat = float(input("  Latitude: "))
    p_lon = float(input("  Longitude: "))

    dist1 = haversine(ueransim_lat, ueransim_lon, i_lat, i_lon)
    dist2 = haversine(i_lat, i_lon, p_lat, p_lon)
    bw1 = calculate_bandwidth(dist1)
    bw2 = calculate_bandwidth(dist2)

    print(f"\nDistance ueransim → i-upf: {dist1:.2f} km → {bw1:.2f} Mbps")
    print(f"Distance i-upf → psa-upf: {dist2:.2f} km → {bw2:.2f} Mbps")

    client = docker.from_env()
    upf_i = client.containers.get("i-upf")
    upf_psa = client.containers.get("psa-upf")

    apply_bandwidth_limit(upf_i, "upfgtp", bw1)
    apply_bandwidth_limit(upf_psa, "upfgtp", bw2)

    logging.info("Bandwidth limitations applied successfully.")

    if args.run_ping:
        if not PING_AVAILABLE:
            logging.error("Ping module not available.")
            sys.exit(1)
        success, results = auth_ping_measure(
            args.num_ues,
            args.packet_size,
            args.config_prefix,
            args.ping_count,
            args.interval,
            args.qos
        )
        if success:
            save_results(results, args.packet_size)
        else:
            sys.exit(1)
        cleanup_ue_interfaces()

if __name__ == "__main__":
    main()
