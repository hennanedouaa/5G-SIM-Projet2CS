#!/usr/bin/env python3
import argparse
import datetime
from utils.measure_traffic_metrics import measure_traffic_metrics

def main():
    parser = argparse.ArgumentParser(description='Measure network metrics between Docker containers using OWAMP')
    parser.add_argument('client', help='Client container name')
    parser.add_argument('server', help='Server container name')
    parser.add_argument('-s', '--size', type=int, default=100, help='Packet size in bytes (default: 100)')
    parser.add_argument('-p', '--count', type=int, default=10, help='Number of packets to send (default: 100)')
    parser.add_argument('-i', '--interval', type=float, default=1, help='Interval between packets in seconds (default: 1)')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print(f"NETWORK METRICS TEST: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client: {args.client} | Server: {args.server}")
    print(f"Parameters: {args.count} packets, {args.size} bytes, {args.interval}s interval")
    print("="*70 + "\n")
    
    measure_traffic_metrics(
        args.client,
        args.server,
        packet_size=args.size,
        packet_count=args.count,
        interval=args.interval,
    )

if __name__ == "__main__":
    main()