import subprocess
import datetime
import re
import os
import threading

results_summary = []  # List to store metrics from all UE interfaces

def get_ue_interfaces(client_container):
    interfaces = subprocess.check_output(["docker", "exec", client_container, "ip", "addr"], text=True)
    ue_ifaces = re.findall(r'\d+: (uesimtun\d+):', interfaces)
    return ue_ifaces

def run_owping_from_interface(client_container, server_ip, iface, packet_size, packet_count, interval, result_file):
    cmd = [
        "docker", "exec", client_container,
        "owping",
        "-c", str(packet_count),
        "-i", str(interval),
        "-s", str(packet_size),
        "-B", "uesimtun1",
        server_ip
    ]

    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        block = output.split('--- owping statistics')[1]

        sent_match = re.search(r'(\d+) sent, (\d+) lost.*?([\d.]+)%', block)
        delay_match = re.search(r'one-way delay min/median/max = ([\d.]+)/([\d.]+)/([\d.]+)', block)
        jitter_match = re.search(r'one-way jitter = ([\d.]+)', block)

        if not (sent_match and delay_match and jitter_match):
            print(f"[ERROR] Failed to parse OWAMP output for {iface}.")
            return

        sent = int(sent_match.group(1))
        lost = int(sent_match.group(2))
        loss_pct = float(sent_match.group(3))
        delay_min = float(delay_match.group(1))
        delay_median = float(delay_match.group(2))
        delay_max = float(delay_match.group(3))
        jitter = float(jitter_match.group(1))

        # Store values for global summary
        results_summary.append({
            "iface": iface,
            "loss_pct": loss_pct,
            "delay_min": delay_min,
            "delay_median": delay_median,
            "delay_max": delay_max,
            "jitter": jitter
        })

        # Write per-interface results
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

        print(f"[✓] {iface}: median={delay_median}ms, loss={loss_pct:.2f}%, jitter={jitter}ms")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed owping from {iface}: {e.output}")

def measure_traffic_metrics(client_container, server_container, packet_size, packet_count, interval):
    global results_summary
    results_summary = []  # Reset results
    result_file = "network_metrics.txt"

    # Get server IP
    server_ip = subprocess.check_output([
        "docker", "inspect", "-f",
        "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
        server_container
    ], text=True).strip()

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"[INFO] Starting OWAMP server on {server_container} ({server_ip})...")
    subprocess.Popen([
        "docker", "exec", server_container, "owampd", "-f", "-v"
    ])
    subprocess.run(["sleep", "2"])

    # Detect UE interfaces
    ue_interfaces = get_ue_interfaces(client_container)
    ue_interfaces = [iface for iface in ue_interfaces if iface != "uesimtun0"]
    if not ue_interfaces:
        print("[ERROR] No UE interfaces found.")
        return

    print(f"[INFO] Found UE interfaces: {', '.join(ue_interfaces)}")
    print("[INFO] Running traffic measurements in parallel... please wait.")

    with open(result_file, "a") as f:
        f.write("\n" + "="*70 + "\n")
        f.write(f"NETWORK METRICS TEST: {timestamp}\n")
        f.write(f"Client: {client_container} | Server: {server_container} ({server_ip})\n")
        f.write(f"Parameters: {packet_count} packets, {packet_size} bytes, {interval}s interval\n")
        f.write("="*70 + "\n")

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

    # Write global summary
    if results_summary:
        avg_latency = sum(r["delay_median"] for r in results_summary) / len(results_summary)
        min_latency = min(r["delay_min"] for r in results_summary)
        max_latency = max(r["delay_max"] for r in results_summary)
        avg_loss = sum(r["loss_pct"] for r in results_summary) / len(results_summary)
        avg_jitter = sum(r["jitter"] for r in results_summary) / len(results_summary)

        summary = "\n" + "="*50 + "\n"
        summary += f"GLOBAL METRICS SUMMARY ({timestamp})\n"
        summary += f"Average Latency (median): {avg_latency:.3f} ms\n"
        summary += f"Minimum Latency: {min_latency:.3f} ms\n"
        summary += f"Maximum Latency: {max_latency:.3f} ms\n"
        summary += f"Average Packet Loss: {avg_loss:.3f}%\n"
        summary += f"Average Jitter: {avg_jitter:.3f} ms\n"
        summary += "="*50 + "\n"

        with open(result_file, "a") as f:
            f.write(summary)

        print(summary)

    print(f"[SUCCESS] All tests completed. Results saved to {result_file}.")
