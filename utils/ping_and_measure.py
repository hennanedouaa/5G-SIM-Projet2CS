
#!/usr/bin/env python3
import subprocess
import re
import os
import sys
import time
from datetime import datetime

# ---- Configuration ----
UERANSIM_CONTAINER = "ueransim"
UPF_CONTAINER = "psa-upf"
RESULTS_FILE = "ping_result.txt"
CONFIG_PREFIX = "config/uecfg"
DEFAULT_PACKET_SIZE = "8"
DEFAULT_QOS = "0xb8"
DEFAULT_INTERVAL = "0.02"


# ---- Get UPF container IP address ----
def get_container_ip(container_name):
    cmd = ["docker", "exec", container_name, "hostname", "-I"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)

    ip_list = result.stdout.strip().split()
    return ip_list[0] if ip_list else None


# ---- Authenticate a UE in the UERANSIM container ----
def authenticate_ue(ue_index, config_prefix=CONFIG_PREFIX, container=UERANSIM_CONTAINER, timeout=30):
    """
        ue_index (int): Index number of the UE
        config_prefix (str): Prefix for config files
    """
    config_file = f"{config_prefix}{ue_index}.yaml"
    print(f"[INFO] Starting authentication for UE {ue_index} using {config_file}")

    # Start UE in background
    cmd = ["docker", "exec", "-d", container, "./nr-ue", "-c", config_file]
    subprocess.run(cmd)

    # Calculate expected interface numbers - modified for single interface per UE
    expected_interface = f"uesimtun{ue_index - 1}"
    expected_interfaces = [expected_interface]

    print(f"[INFO] Waiting for interface {expected_interface} to be created...")
    # Wait for interfaces to be created
    start_time = time.time()
    interfaces_found = []

    while time.time() - start_time < timeout:
        cmd = ["docker", "exec", container, "ip", "a"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        output = result.stdout

        interfaces_found = []
        for interface in expected_interfaces:
            if interface in output:
                interfaces_found.append(interface)

        if len(interfaces_found) == len(expected_interfaces):
            print(f"[SUCCESS] UE {ue_index} authenticated successfully, interfaces created: {', '.join(interfaces_found)}")
            return True, interfaces_found

        time.sleep(1)

    print(f"[ERROR] Timeout waiting for UE {ue_index} interfaces. Found: {', '.join(interfaces_found)}")
    return False, interfaces_found

# ---- Run ping from UE to UPF ----
def ping_from_interface(interface, destination_ip, packet_size=DEFAULT_PACKET_SIZE,
                        count=5, interval=DEFAULT_INTERVAL, qos=DEFAULT_QOS, container=UERANSIM_CONTAINER):

    print(f"[INFO] Pinging {destination_ip} from interface {interface} with packet size {packet_size}...")

    cmd = ["docker", "exec", container, "ping",
           "-I", interface,
           "-s", str(packet_size),
           "-i", str(interval),
           "-Q", str(qos),
           "-c", str(count),
           destination_ip]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout

    # ---- Parse ping output for average RTT and packet loss ----
    rtt_match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+ ms", output)
    loss_match = re.search(r"(\d+)% packet loss", output)

    results = {
        'interface': interface,
        'destination': destination_ip,
        'packet_size': packet_size,
        'qos': qos,
        'rtt': rtt_match.group(1) if rtt_match else "N/A",
        'loss': loss_match.group(1) if loss_match else "N/A",
        'success': "0%" in output and rtt_match is not None,
        'raw_output': output
    }

    status = "✓" if results['success'] else "✗"
    print(f"[{status}] Interface {interface}: RTT={results['rtt']}ms, Loss={results['loss']}%")

    return results


def save_results(results_list, packet_size):
    """Save test results to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(RESULTS_FILE, "a") as f:
        f.write(f"\n=== Ping Test at {timestamp} ===\n")
        f.write(f"Packet Size: {packet_size} bytes\n")

        for result in results_list:
            f.write(f"\nInterface: {result['interface']}\n")
            f.write(f"Destination IP: {result['destination']}\n")
            f.write(f"QoS: {result['qos']}\n")
            f.write(f"Average RTT: {result['rtt']} ms\n")
            f.write(f"Packet Loss: {result['loss']} %\n")
            f.write(f"Success: {'Yes' if result['success'] else 'No'}\n")

    print(f"[INFO] Results saved to {RESULTS_FILE}")

# ---- Clean up uesimtun interfaces in the container ----
def cleanup_ue_interfaces(container=UERANSIM_CONTAINER):
    print("[INFO] Cleaning up UE interfaces...")
    cmd = ["docker", "exec", container, "bash", "-c", "for i in $(ip a | grep -o 'uesimtun[0-9]\\+'); do ip link delete $i; done"]
    subprocess.run(cmd)
    time.sleep(2)


# ---- Authenticate UEs and perform ping measurements ----
def auth_ping_measure(num_ues, packet_size, config_prefix, ping_count, interval, qos):
    # ---- Get UPF IP using container name ----
    upf_ip = get_container_ip(UPF_CONTAINER)
    if not upf_ip:
        print(f"[ERROR] Failed to get IP address for container '{UPF_CONTAINER}'")
        return False, []

    print(f"[INFO] Found UPF container '{UPF_CONTAINER}' with IP: {upf_ip}")

    all_results = []
    data_interfaces = []

    # ---- Authenticate each UE ----
    for i in range(1, num_ues + 1):
      success, interfaces = authenticate_ue(
        i,
        config_prefix=config_prefix,
        container=UERANSIM_CONTAINER
      )

      if success:
        # All interfaces are data interfaces in this case
        data_interfaces.extend(interfaces)

    # ---- Wait for network stability ----
    if data_interfaces:
        print(f"\n[INFO] Found {len(data_interfaces)} data interfaces: {', '.join(data_interfaces)}")
        print("[INFO] Waiting 3 seconds for network stability...")
        time.sleep(3)

        for interface in data_interfaces:
            result = ping_from_interface(
                interface,
                upf_ip,
                packet_size=packet_size,
                count=ping_count,
                interval=interval,
                qos=qos,
                container=UERANSIM_CONTAINER
            )
            all_results.append(result)

        return True, all_results
    else:
        print("[ERROR] No data interfaces found. Authentication may have failed.")
        return False, []