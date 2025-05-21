#!/usr/bin/env python3
import sys
import logging
import time
from math import radians, sin, cos, sqrt, atan2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1 - a))

def get_network_interface(container, target_ip=None):
    try:
        result = container.exec_run("ip -o link show", privileged=True)
        links = result.output.decode().splitlines()
        for line in links:
            if "gtp" in line.lower():
                iface = line.split(":")[1].strip()
                logging.info(f"Detected GTP interface: {iface}")
                return iface

        result = container.exec_run("ip -o route", privileged=True)
        routes = result.output.decode().splitlines()
        for line in routes:
            parts = line.split()
            if len(parts) >= 5:
                dest = parts[1]
                iface = parts[-1]
                if dest != "default":
                    logging.info(f"Fallback interface from route table: {iface}")
                    return iface

        result = container.exec_run("ip route | awk '/default/ {print $5}'", privileged=True)
        fallback_iface = result.output.decode().strip() or 'eth1'
        logging.info(f"Using fallback default interface: {fallback_iface}")
        return fallback_iface

    except Exception as e:
        logging.error(f"Error detecting network interface: {e}")
        return 'eth1'

def clear_existing_rules(container, iface):
    cmds = [
        f"tc qdisc del dev {iface} root 2>/dev/null",
        f"tc qdisc del dev {iface} root 2>/dev/null || true",
        f"tc qdisc replace dev {iface} root pfifo_fast"
    ]
    for cmd in cmds:
        result = container.exec_run(cmd, privileged=True)
        time.sleep(1)
        if result.exit_code == 0:
            return True
    return False

def apply_bandwidth_limit(container, iface, bw):
    max_retries = 5
    latency_ms = 10
    for attempt in range(1, max_retries + 1):
        try:
            container.exec_run(
                f"tc qdisc replace dev {iface} root pfifo_fast",
                privileged=True
            )
            time.sleep(1)
            bw_kbits = bw * 1000
            burst_kb = int((bw_kbits * latency_ms) / (8 * 1000))
            cmd = (
                f"tc qdisc replace dev {iface} root tbf "
                f"rate {bw:.0f}mbit burst {burst_kb}Kb latency {latency_ms}ms"
            )
            logging.info(f"Attempt {attempt}: {cmd}")
            result = container.exec_run(cmd, privileged=True)
            if result.exit_code == 0:
                return True
            output = result.output.decode()
            if "Exclusivity flag on" in output:
                logging.warning(f"TC locked (attempt {attempt}), waiting...")
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(output)
        except Exception as e:
            logging.error(f"Attempt {attempt} failed: {str(e)}")
            if attempt == max_retries:
                raise RuntimeError(f"Failed after {max_retries} attempts: {str(e)}")
            time.sleep(attempt * 2)

def get_bandwidth_before(container, iface):
    try:
        result = container.exec_run(f"ethtool {iface}", privileged=True)
        output = result.output.decode()
        for line in output.splitlines():
            if "Speed" in line:
                speed = line.split(":")[1].strip()
                logging.info(f"Bandwidth for {iface} using ethtool: {speed}")
                return int(speed.split("Mb")[0])
        result = container.exec_run(f"ip -s link show {iface}", privileged=True)
        output = result.output.decode()
        for line in output.splitlines():
            if "RX" in line or "TX" in line:
                logging.info(f"Bandwidth for {iface} using ip command (approximated): 1000 Mbps")
                return 1000
    except Exception as e:
        logging.error(f"Error fetching bandwidth info: {e}")
        return 1000



def apply_distance(upf_coords, attenuation_db_per_km=0.02, min_bandwidth=100):
    """
    Applies bandwidth degradation based on distance between UPFs using Docker and tc.

    Args:
        upf_coords (dict): Dictionary of UPF names and their GPS coordinates.
            Example: { "upf-1": {"x": 36.75, "y": 3.06}, "upf-2": {"x": 36.78, "y": 3.08} }
        attenuation_db_per_km (float): Attenuation in dB/km for fiber optics.
        min_bandwidth (int): Minimum bandwidth floor in Mbps.
    """
    try:
        import docker
    except ImportError:
        logging.error("Install docker SDK: pip3 install docker")
        return

    try:
        client = docker.from_env()
        links = list(zip(upf_coords.keys(), list(upf_coords.keys())[1:]))  # pair sequentially

        upfs = {}
        for name, pos in upf_coords.items():
            container = client.containers.get(name)
            coords = (pos["x"], pos["y"])
            iface = get_network_interface(container)
            original_bw = get_bandwidth_before(container, iface)

            upfs[name] = {
                "container": container,
                "coords": coords,
                "iface": iface,
                "original_bw": original_bw
            }

        def haversine_km(a, b):
            return haversine(*a["coords"], *b["coords"])

        def calculate_bw(distance_km, original_bw):
            return max(original_bw * (10 ** (-attenuation_db_per_km * distance_km / 10)), min_bandwidth)

        for upf1_name, upf2_name in links:
            try:
                upf1 = upfs[upf1_name]
                upf2 = upfs[upf2_name]

                distance_km = haversine_km(upf1, upf2)
                bw1 = calculate_bw(distance_km, upf1["original_bw"])
                bw2 = calculate_bw(distance_km, upf2["original_bw"])

                clear_existing_rules(upf1["container"], upf1["iface"])
                clear_existing_rules(upf2["container"], upf2["iface"])

                success1 = apply_bandwidth_limit(upf1["container"], upf1["iface"], bw1)
                success2 = apply_bandwidth_limit(upf2["container"], upf2["iface"], bw2)

                if success1 and success2:
                    logging.info(
                        f"Link {upf1_name} <-> {upf2_name} ({distance_km:.2f} km): "
                        f"{bw1:.0f} Mbps for {upf1_name}, {bw2:.0f} Mbps for {upf2_name}"
                    )
                else:
                    raise RuntimeError("One or both bandwidth applications failed")

            except Exception as e:
                logging.error(f"Error applying distance between {upf1_name} and {upf2_name}: {e}")

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")

