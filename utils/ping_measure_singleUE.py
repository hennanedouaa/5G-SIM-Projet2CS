#!/usr/bin/env python3
import subprocess
import re
import sys
from datetime import datetime

# ---- Configuration ----
RESULTS_FILE = "ping_result_one.txt"
DEFAULT_QOS = "0xb8"
DEFAULT_INTERVAL = "0.02"
DEFAULT_COUNT = 5

# ---- Handle command line arguments ----
if len(sys.argv) != 4:
    print("Usage: python ping_direct_ue_to_upf.py <UE_CONTAINER> <UPF_CONTAINER> <packet_size>")
    sys.exit(1)

UE_CONTAINER = sys.argv[1]
UPF_CONTAINER = sys.argv[2]
packet_size = sys.argv[3]

# ---- Get container IP address by name ----
def get_container_ip(container_name):
    cmd = ["docker", "exec", container_name, "hostname", "-I"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    ip_list = result.stdout.strip().split()
    return ip_list[0] if ip_list else None

# ---- Run ping from UERANSIM container to UPF ----
def run_ping(upf_ip, packet_size):
    print(f"[INFO] Running ping to {upf_ip} with packet size {packet_size}...")
    cmd = [
        "docker", "exec", UE_CONTAINER,
        "ping", "-c", str(DEFAULT_COUNT),
        "-s", str(packet_size),
        "-Q", str(DEFAULT_QOS),
        "-i", str(DEFAULT_INTERVAL),
        upf_ip
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout

# ---- Parse ping output for RTT and packet loss ----
def parse_ping_output(output):
    rtt_match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+ ms", output)
    loss_match = re.search(r"(\d+)% packet loss", output)

    rtt = rtt_match.group(1) if rtt_match else "N/A"
    loss = loss_match.group(1) if loss_match else "N/A"
    return rtt, loss

# ---- Save results ----
def save_results(ue_ip, upf_ip, rtt, loss, packet_size):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(RESULTS_FILE, "a") as f:
        f.write(f"\n=== Ping Test at {timestamp} ===\n")
        f.write(f"UE IP: {ue_ip}\n")
        f.write(f"UPF IP: {upf_ip}\n")
        f.write(f"Packet Size: {packet_size} bytes\n")
        f.write(f"Average RTT: {rtt} ms\n")
        f.write(f"Packet Loss: {loss} %\n")
    print(f"[INFO] Results saved to {RESULTS_FILE}")

# ---- Main ----
def main():
    print(f"[INFO] Starting direct ping test with packet size = {packet_size} bytes...")
    upf_ip = get_container_ip(UPF_CONTAINER)
    ue_ip = get_container_ip(UE_CONTAINER)

    if not upf_ip:
        print(f"[ERROR] Could not retrieve IP for UPF container '{UPF_CONTAINER}'")
        sys.exit(1)
    if not ue_ip:
        print(f"[ERROR] Could not retrieve IP for UE container '{UE_CONTAINER}'")
        sys.exit(1)

    ping_output = run_ping(upf_ip, packet_size)
    rtt, loss = parse_ping_output(ping_output)
    save_results(ue_ip, upf_ip, rtt, loss, packet_size)

if __name__ == "__main__":
    main()
