import subprocess
import datetime
import re
import os
import threading

def get_ue_interfaces(client_container):
    interfaces = subprocess.check_output(["docker", "exec", client_container, "ip", "addr"], text=True)

    # Extract interfaces that likely belong to UE (adjust this regex if needed)
    ue_ifaces = re.findall(r'\d+: (uesimtun\d+):', interfaces)
    return ue_ifaces

def run_owping_from_interface(client_container, server_ip, iface, packet_size, packet_count, interval, result_file):
    cmd = [
        "docker", "exec", client_container,
        "owping",
        "-c", str(packet_count),
        "-i", str(interval),
        "-s", str(packet_size),
        "-B", iface,
        server_ip
    ]

    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        block = output.split('--- owping statistics')[1].split('--- owping statistics')[0]

        sent_match = re.search(r'(\d+) sent, (\d+) lost.*?([\d.]+)%', block)
        delay_match = re.search(r'one-way delay min/median/max = ([\d.]+)/([\d.]+)/([\d.]+)', block)
        jitter_match = re.search(r'one-way jitter = ([\d.]+)', block)

        if not (sent_match and delay_match and jitter_match):
            print(f"[ERROR] Failed to parse OWAMP output for {iface}.")
            return

        sent = int(sent_match.group(1))
        lost = int(sent_match.group(2))
        loss_pct = float(sent_match.group(3))
        delay_min, delay_median, delay_max = delay_match.groups()
        jitter = jitter_match.group(1)

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        results = f"\n{'='*50}\n"
        results += f"TEST TIMESTAMP: {timestamp}\n"
        results += f"Client Interface: {iface} ({client_container}) → {server_ip}\n"
        results += f"Packet Size: {packet_size} bytes\n"
        results += f"Packet Count: {packet_count}\n"
        results += f"Interval: {interval}s\n"
        results += f"Packets Sent: {sent}\n"
        results += f"Packets Lost: {lost}\n"
        results += f"Packet Loss: {loss_pct:.3f}%\n"
        results += f"One-way Delay (ms): min={delay_min}, median={delay_median}, max={delay_max}\n"
        results += f"One-way Jitter (ms): {jitter}\n"
        results += f"{'='*50}\n"

        with open(result_file, "a") as f:
            f.write(results)

        print(f"[✓] {iface}: {sent} packets sent, {lost} lost ({loss_pct:.3f}%), median delay: {delay_median}ms")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed owping from {iface}: {e.output}")

def measure_traffic_metrics(client_container, server_container, packet_size, packet_count, interval):
    result_file = "network_metrics.txt"

    # Get server IP
    server_ip = subprocess.check_output([
        "docker", "inspect", "-f",
        "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
        server_container
    ], text=True).strip()

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Start OWAMP server
    print(f"[INFO] Starting OWAMP server on {server_container} ({server_ip})...")
    subprocess.Popen([
        "docker", "exec", server_container, "owampd", "-f", "-v"
    ])
    subprocess.run(["sleep", "2"])

    # Detect UE interfaces
    ue_interfaces = get_ue_interfaces(client_container)
    if not ue_interfaces:
        print("[ERROR] No UE interfaces found.")
        return

    print(f"[INFO] Found UE interfaces: {', '.join(ue_interfaces)}")
    print("[INFO] Running traffic measurements in parallel... please wait.")


    # Write header block once for the whole test
    with open(result_file, "a") as f:
        f.write("\n" + "="*70 + "\n")
        f.write(f"NETWORK METRICS TEST: {timestamp}\n")
        f.write(f"Client: {client_container} | Server: {server_container} ({server_ip})\n")
        f.write(f"Parameters: {packet_count} packets, {packet_size} bytes, {interval}s interval\n")
        f.write("="*70 + "\n")

    # Launch all owping tests in parallel threads
    threads = []
    for iface in ue_interfaces:
        t = threading.Thread(
            target=run_owping_from_interface,
            args=(client_container, server_ip, iface, packet_size, packet_count, interval, result_file)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Close block after all tests
    with open(result_file, "a") as f:
        f.write("="*70 + "\n")

    print(f"[SUCCESS] All tests completed. Results saved to {result_file}.")