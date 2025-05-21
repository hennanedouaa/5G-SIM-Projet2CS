import subprocess
import datetime
import re
import os

def measure_traffic_metrics(client_container, server_container, packet_size, packet_count, interval):
    result_file="network_metrics.txt"
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get server IP
    server_ip = subprocess.check_output([
        "docker", "inspect", "-f", 
        "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", 
        server_container
    ], text=True).strip()
    
    # Start owampd server
    print(f"[INFO] Starting OWAMP server on {server_container} ({server_ip})...")
    subprocess.Popen([
        "docker", "exec", server_container, "owampd", "-f", "-v"
    ])
    print(f"[INFO] Waiting for server to initialize...")
    subprocess.run(["sleep", "2"])
    print(f"[INFO] OWAMP server ready")
    
    # Run owping from client to server
    print(f"[INFO] Sending {packet_count} packets of {packet_size} bytes from {client_container} to {server_ip}...")
    print(f"[INFO] Packet interval: {interval}s")
    cmd = [
        "docker", "exec", client_container,
        "owping", "-c", str(packet_count),
        "-i", str(interval),
        "-s", str(packet_size),
        server_ip
    ]
    print(f"[INFO] Test in progress, please wait...")
    output = subprocess.check_output(cmd, text=True)
    print(f"[INFO] Test completed, analyzing results...")
    
    # Extract the first statistics block only (client → server)
    block = output.split('--- owping statistics')[1].split('--- owping statistics')[0]
    
    # Parse key values
    sent_match = re.search(r'(\d+) sent, (\d+) lost.*?([\d.]+)%', block)
    delay_match = re.search(r'one-way delay min/median/max = ([\d.]+)/([\d.]+)/([\d.]+)', block)
    jitter_match = re.search(r'one-way jitter = ([\d.]+)', block)
    
    if not (sent_match and delay_match and jitter_match):
        print("[ERROR] Failed to parse OWAMP output.")
        return None
    
    sent = int(sent_match.group(1))
    lost = int(sent_match.group(2))
    loss_pct = float(sent_match.group(3))
    delay_min, delay_median, delay_max = delay_match.groups()
    jitter = jitter_match.group(1)
    
    # Prepare test results
    results = f"\n{'='*50}\n"
    results += f"TEST TIMESTAMP: {timestamp}\n"
    results += f"Client → Server: {client_container} → {server_container}\n"
    results += f"Server IP: {server_ip}\n"
    results += f"Packet Size: {packet_size} bytes\n"
    results += f"Packet Count: {packet_count}\n"
    results += f"Interval: {interval}s\n"
    results += f"Packets Sent: {sent}\n"
    results += f"Packets Lost: {lost}\n"
    results += f"Packet Loss: {loss_pct:.3f}%\n"
    results += f"One-way Delay (ms): min={delay_min}, median={delay_median}, max={delay_max}\n"
    results += f"One-way Jitter (ms): {jitter}\n"
    results += f"{'='*50}\n"
    
    # Append results to the file
    file_exists = os.path.isfile(result_file)
    with open(result_file, "a") as f:
        if not file_exists:
            f.write("NETWORK METRICS TEST RESULTS\n\n")
        f.write(results)
    
    print(f"[SUCCESS] Test results successfully appended to: {result_file}")
    print(f"[✓] Summary: {sent} packets sent, {lost} lost ({loss_pct:.3f}%), median delay: {delay_median}ms")
    return result_file