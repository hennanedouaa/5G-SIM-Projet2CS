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
    """Calculate distance between two GPS points (in km)"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1-a))

def calculate_bandwidth(distance_km):
    """Calculate bandwidth based on distance with fiber attenuation model"""
    return max(10000 * (10 ** (-0.22 * distance_km / 10)), 100)  # Min 100Mbps

def get_network_interface(container):
    """Safely determine the network interface"""
    for iface in ['gtp0', 'upfgtp', 'eth0', 'eth1']:
        result = container.exec_run(f"ip link show {iface}", privileged=True)
        if result.exit_code == 0:
            return iface
    result = container.exec_run("ip route | awk '/default/ {print $5}'", privileged=True)
    return result.output.decode().strip() or 'eth0'

def clear_existing_rules(container, iface):
    """Forcefully clear all existing tc rules"""
    cmds = [
        f"tc qdisc del dev {iface} root 2>/dev/null",
        f"tc qdisc del dev {iface} ingress 2>/dev/null",
        f"tc qdisc del dev {iface} root 2>/dev/null || true"
    ]
    for cmd in cmds:
        container.exec_run(cmd, privileged=True)
        time.sleep(0.1)
    return True

def apply_bandwidth_limit(container, iface, bw):
    """Apply bandwidth limit with optimized burst/latency"""
    max_retries = 5
    latency_ms = 2  # uRLLC target (2ms)
    
    for attempt in range(1, max_retries + 1):
        try:
            clear_existing_rules(container, iface)
            
            # Calculate burst in BYTES (tc expects bytes for burst parameter)
            bw_bytes_per_sec = (bw * 10**6) / 8  # Convert Mbps to bytes/sec
            burst_bytes = int(bw_bytes_per_sec * (latency_ms / 1000))
            
            cmd = (
                f"tc qdisc add dev {iface} root tbf "
                f"rate {bw}mbit burst {burst_bytes} latency {latency_ms}ms"
            )
            result = container.exec_run(cmd, privileged=True)
            
            if result.exit_code == 0:
                logging.info(
                    f"Applied TBF: {bw}Mbps, "
                    f"burst={burst_bytes}bytes, "
                    f"latency={latency_ms}ms"
                )
                return True
                
            if "Exclusivity flag on" in result.output.decode():
                time.sleep(attempt * 1.5)  # Exponential backoff
                continue
                
            raise RuntimeError(result.output.decode())
            
        except Exception as e:
            logging.error(f"Attempt {attempt} failed: {str(e)}")
            if attempt == max_retries:
                raise
            time.sleep(attempt * 1.5)

def get_container_coords(container):
    """Get coordinates from container environment or labels"""
    try:
        # Try environment variables first
        env = {e.split('=')[0]: e.split('=')[1] 
               for e in container.attrs['Config']['Env']}
        if 'LATITUDE' in env and 'LONGITUDE' in env:
            return float(env['LATITUDE']), float(env['LONGITUDE'])
        
        # Fallback to labels
        loc = container.labels.get('location', '').split(',')
        if len(loc) == 2:
            return float(loc[0]), float(loc[1])
            
        raise ValueError("No coordinates found in env or labels")
    except Exception as e:
        logging.error(f"Coordinate error: {str(e)}")
        raise

def main():
    try:
        import docker
    except ImportError:
        logging.error("Install docker SDK: pip3 install docker")
        sys.exit(1)

    try:
        client = docker.from_env()
        amf = client.containers.get("amf")
        upf = client.containers.get("upf")

        # Get coordinates and calculate distance
        amf_lat, amf_lon = get_container_coords(amf)
        upf_lat, upf_lon = get_container_coords(upf)
        distance_km = haversine(amf_lat, amf_lon, upf_lat, upf_lon)
        bw = calculate_bandwidth(distance_km)

        # Configure UPF interface
        iface = get_network_interface(upf)
        if apply_bandwidth_limit(upf, iface, bw):
            logging.info(
                f"Successfully configured {iface}: "
                f"{distance_km:.1f}km → {bw:.0f}Mbps"
            )
        else:
            raise RuntimeError("Failed after retries")

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()