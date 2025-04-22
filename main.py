import logging
import sys
from utils.calculate_distance import apply_bandwidth_limit, calculate_bandwidth, haversine
from utils.distance_simulation import get_ueransim_coords_from_docker_compose, prompt_for_coordinates
from utils.ping_and_measure import auth_ping_measure

def main():
    try:
        # Import docker module at the beginning
        try:
            import docker
        except ImportError:
            logging.error("Install docker SDK: pip3 install docker")
            sys.exit(1)
            
        # Get UERANSIM coordinates from docker-compose file
        ueransim_lat, ueransim_lon = get_ueransim_coords_from_docker_compose()
        
        # Prompt user for i-upf and psa-upf coordinates
        i_upf_lat, i_upf_lon, psa_upf_lat, psa_upf_lon = prompt_for_coordinates(
            ueransim_lat, ueransim_lon
        )
        
        # Calculate distances
        distance_ue_upfi = haversine(ueransim_lat, ueransim_lon, i_upf_lat, i_upf_lon)
        distance_upfi_psa = haversine(i_upf_lat, i_upf_lon, psa_upf_lat, psa_upf_lon)
        
        # Calculate bandwidths
        bw_ue_upfi = calculate_bandwidth(distance_ue_upfi)
        bw_upfi_psa = calculate_bandwidth(distance_upfi_psa)
        
        # Display results
        print("\nRésultats calculés:")
        print(f"Distance ueransim → i-upf: {distance_ue_upfi:.2f} km")
        print(f"Bande passante estimée: {bw_ue_upfi:.2f} Mbps")
        print(f"Distance i-upf → psa-upf: {distance_upfi_psa:.2f} km")
        print(f"Bande passante estimée: {bw_upfi_psa:.2f} Mbps")
        
        # Now always apply bandwidth limitations without asking
        print("\nApplication des limitations de bande passante aux conteneurs...")
                
        client = docker.from_env()
        
        try:
            # Get containers
            ueransim = client.containers.get("ueransim")
            upf_i = client.containers.get("i-upf")
            upf_psa = client.containers.get("psa-upf")
            
            # Set network interfaces
            i_upf_iface = "upfgtp"
            psa_upf_iface = "upfgtp"
            
            # Apply bandwidth limitations
            # ue - i-upf
            apply_bandwidth_limit(upf_i, i_upf_iface, bw_ue_upfi)
            logging.info(f"Limitation entre ueransim → i-upf : {distance_ue_upfi:.1f}km, {bw_ue_upfi:.2f} Mbps")
            
            # i-upf -- psa-upf
            apply_bandwidth_limit(upf_psa, psa_upf_iface, bw_upfi_psa)
            logging.info(f"Limitation entre i-upf → psa-upf : {distance_upfi_psa:.1f}km, {bw_upfi_psa:.2f} Mbps")
            
            print("\nLimitations de bande passante appliquées avec succès!")
            
        except Exception as e:
            logging.error(f"Erreur lors de l'application des limitations: {str(e)}")
            sys.exit(1)
        
        sys.exit(0)

        num_ues = 1
        packet_size = "64"           # Optional: use DEFAULT_PACKET_SIZE if you prefer
        config_prefix = "config/uecfg"
        ping_count = 10
        interval = "0.02"            # Optional: use DEFAULT_INTERVAL
        qos = "0xb8"                 # Optional: use DEFAULT_QOS

        success, results = auth_ping_measure(
            num_ues=num_ues,
            packet_size=packet_size,
            config_prefix=config_prefix,
            ping_count=ping_count,
            interval=interval,
            qos=qos
            )

        if success:
            print("[INFO] Ping test completed successfully.")
        else:
            print("[ERROR] Ping test failed.")
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
