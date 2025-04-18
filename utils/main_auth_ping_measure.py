#!/usr/bin/env python3
import argparse
import sys
from ping_and_measure import (
    auth_ping_measure, save_results, cleanup_ue_interfaces
)

def main():
    # Define command line arguments
    parser = argparse.ArgumentParser(description='Free5GC Network Testing Tool')
    parser.add_argument('-n', '--num_ues', type=int, default=1, help='Number of UEs to authenticate')
    parser.add_argument('-s', '--packet_size', type=str, default='8', help='Ping packet size in bytes')
    parser.add_argument('-c', '--config_prefix', type=str, default='config/uecfg', help='Prefix for UE config files')
    parser.add_argument('-r', '--restart', action='store_true', help='Restart all UE processes')
    parser.add_argument('-p', '--ping_count', type=int, default=5, help='Number of ping packets per interface')
    parser.add_argument('-i', '--interval', type=str, default='0.02', help='Interval between pings in seconds')
    parser.add_argument('-q', '--qos', type=str, default='0xb8', help='QoS value in hex format')
    args = parser.parse_args()

    print("\n=== Free5GC Network Testing Tool ===\n")
    
    # ---- Calling the function that does the authentication and measurement ----
    success, all_results = auth_ping_measure(
        args.num_ues,
        args.packet_size,
        args.config_prefix,
        args.ping_count,
        args.interval,
        args.qos
    )
    
    if success:
        # Save results
        save_results(all_results, args.packet_size)
    else:
        sys.exit(1)
        
    # Clean up UE interfaces
    cleanup_ue_interfaces()

if __name__ == "__main__":
    main()