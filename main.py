#!/usr/bin/env python3
import argparse
import sys
import logging
from utils.apply_distance import prompt_for_coordinates, apply_distance
from utils.ping_and_measure import (
    auth_ping_measure, save_results, cleanup_ue_interfaces
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    # Define command line arguments
    parser = argparse.ArgumentParser(description='Free5GC Network Testing Tool with Distance Simulation')
    parser.add_argument('--skip-distance', action='store_true', help='Skip distance configuration')
    parser.add_argument('-n', '--num_ues', type=int, default=1, help='Number of UEs to authenticate')
    parser.add_argument('-s', '--packet_size', type=str, default='8', help='Ping packet size in bytes')
    parser.add_argument('-c', '--config_prefix', type=str, default='config/uecfg', help='Prefix for UE config files')
    parser.add_argument('-r', '--restart', action='store_true', help='Restart all UE processes')
    parser.add_argument('-p', '--ping_count', type=int, default=5, help='Number of ping packets per interface')
    parser.add_argument('-i', '--interval', type=str, default='0.02', help='Interval between pings in seconds')
    parser.add_argument('-q', '--qos', type=str, default='0xb8', help='QoS value in hex format')
    parser.add_argument('--skip-ping', action='store_true', help='Skip ping measurements')
    args = parser.parse_args()

    print("\n=== Free5GC Network Testing Tool ===\n")
    
    # Step 1: Configure distance-based bandwidth limitations (unless skipped)
    if not args.skip_distance:
        print("\n=== Configuration des limitations de bande passante basées sur la distance ===\n")
        coordinates = prompt_for_coordinates() 
        success = apply_distance(coordinates)
        if success:
            print("Configuration des distances terminée avec succès.")
        else:
            print("Erreur lors de la configuration des distances.")
            if not args.skip_ping:
                user_continue = input("Voulez-vous continuer avec les tests ping malgré l'erreur ? (o/n): ")
                if user_continue.lower() != 'o':
                    sys.exit(1)
    
    # Step 2: Perform ping measurements (unless skipped)
    if not args.skip_ping:
        print("\n=== Exécution des tests de ping ===\n")
        try:
            # Clean up UE interfaces first if restart flag is set
            if args.restart:
                cleanup_ue_interfaces()
                
            # Perform authentication and ping measurements
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
                print("Tests de ping terminés avec succès.")
            else:
                print("Erreur lors des tests de ping.")
                sys.exit(1)
                
            # Clean up UE interfaces
            cleanup_ue_interfaces()
            
        except Exception as e:
            logging.error(f"Erreur lors des tests de ping: {str(e)}")
            sys.exit(1)
    
    print("\n=== Traitement terminé ===")

if __name__ == "__main__":
    main()