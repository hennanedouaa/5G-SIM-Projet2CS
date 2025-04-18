import subprocess
import re
import os
import sys
from datetime import datetime

# ---- Configuration ----
UE_CONTAINER = "ueransim"
UPF_IMAGE = "free5gc/upf:v4.0.0"
RESULTS_FILE = "ping_result.txt"

# ---- Handle packet size argument ----
if len(sys.argv) != 2:
    print("Usage: python ping_and_measure.py <packet_size>")
    sys.exit(1)

packet_size = sys.argv[1]

# ---- Inform the user the script started ----
print(f"[INFO] Starting ping test with packet size = {packet_size} bytes...")

# ---- Get UPF container ID ----
def get_upf_container_id():
    cmd = ["docker", "ps", "--filter", f"ancestor={UPF_IMAGE}", "--format", "{{.ID}}"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    container_id = result.stdout.strip()
    if not container_id:
        raise Exception("UPF container not found")
    return container_id

# ---- Get UPF container IP address ----
def get_container_ip(container_id):
    cmd = ["docker", "exec", container_id, "hostname", "-I"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    ip_list = result.stdout.strip().split()
    return ip_list[0] if ip_list else None

# ---- Get UE container IP address ----
def get_ue_ip():
    cmd = ["docker", "exec", UE_CONTAINER, "hostname", "-I"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    ip_list = result.stdout.strip().split()
    return ip_list[0] if ip_list else None

# ---- Run ping from UE to UPF ----
def run_ping(ue_container, destination_ip, packet_size):
    cmd = [
        "docker", "exec", ue_container,
        "ping", "-c", "3", "-s", packet_size, destination_ip
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout

# ---- Parse ping output for average RTT and packet loss ----
def parse_ping_output(output):
    rtt_match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+ ms", output)
    loss_match = re.search(r"(\d+)% packet loss", output)

    rtt = rtt_match.group(1) if rtt_match else "N/A"
    loss = loss_match.group(1) if loss_match else "N/A"
    return rtt, loss

# ---- Main Execution ----
try:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upf_id = get_upf_container_id()
    upf_ip = get_container_ip(upf_id)
    ue_ip = get_ue_ip()

    print(f"[INFO] UPF IP: {upf_ip}, UE IP: {ue_ip}")

    ping_output = run_ping(UE_CONTAINER, upf_ip, packet_size)
    rtt, loss = parse_ping_output(ping_output)

    with open(RESULTS_FILE, "a") as f:
        f.write(f"\n=== Ping Test at {timestamp} ===\n")
        f.write(f"UE IP: {ue_ip}\n")
        f.write(f"Destination (UPF) IP: {upf_ip}\n")
        f.write(f"Packet Size: {packet_size} bytes\n")
        f.write(f"Average RTT: {rtt} ms\n")
        f.write(f"Packet Loss: {loss} %\n")

    print("[INFO] Ping test completed and saved to", RESULTS_FILE)

except Exception as e:
    print("[ERROR]", str(e))