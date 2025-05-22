#!/usr/bin/env python3
import os
import yaml
import subprocess
import time
import docker
import sys
from datetime import datetime
from colorama import init, Fore, Style

# Import modules from utils
from utils.distance import apply_distance
from utils.insert import login, insert_ue
from utils.generate_upf_configs import (
    generate_upf_config,
    generate_docker_compose,
    generate_smf_config,
    generate_uerouting_config
)
from utils.measure_traffic_metrics import measure_traffic_metrics

# Initialize colorama for colored terminal output
init(autoreset=True)

def print_header():
    """Print a nice header for the application"""
    header = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════╗
║ {Fore.YELLOW}5G Network Configuration Manager{Fore.CYAN}                            ║
╚═══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """
    print(header)

def print_section(title):
    """Print a section header"""
    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.GREEN}===  {Fore.YELLOW}{title}{Fore.GREEN}  {'='*(63-len(title))}")
    print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}\n")

def print_success(message):
    """Print a success message"""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_info(message):
    """Print an information message"""
    print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")

def print_warning(message):
    """Print a warning message"""
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

def print_error(message):
    """Print an error message"""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def get_user_input(prompt, default=None, is_int=False, min_value=None, max_value=None):
    """Get user input with validation"""
    while True:
        if default is not None:
            user_input = input(f"{Fore.CYAN}{prompt} [{default}]: {Style.RESET_ALL}")
            if user_input.strip() == "":
                user_input = default
        else:
            user_input = input(f"{Fore.CYAN}{prompt}: {Style.RESET_ALL}")
        
        if is_int:
            try:
                value = int(user_input)
                if min_value is not None and value < min_value:
                    print_error(f"Value must be at least {min_value}")
                    continue
                if max_value is not None and value > max_value:
                    print_error(f"Value must be at most {max_value}")
                    continue
                return value
            except ValueError:
                print_error("Please enter a valid number")
        else:
            return user_input

def generate_ue_configs(requested_ues):
    """Generate UE configuration files - generates requested_ues + 1 without mentioning it"""
    print_section("Generating UE Configuration Files")
    
    # Silently add 1 to the requested number
    total_ues = requested_ues + 1
    
    # Paths
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(scripts_dir, 'config/custom/ue')

    # Check if directory exists
    if not os.path.exists(config_dir):
        print_info(f"Creating directory {config_dir}")
        os.makedirs(config_dir, exist_ok=True)

    # List existing UE files
    existing_ues = [f for f in os.listdir(config_dir)
                   if f.startswith('uecfg') and f.endswith('.yaml')]
    existing_count = len(existing_ues)

    # Check if we already have enough files
    if existing_count >= total_ues:
        print_info(f"There are already {existing_count} UE files (total requested: {requested_ues})")
        return

    # Tenant ID
    tenant_id = "6b8d30f1-c2a4-47e3-989b-72511aef87d8"

    # Load template configuration
    template_path = os.path.join(config_dir, 'uecfg1.yaml')
    if not os.path.exists(template_path):
        print_error(f"Template file {template_path} does not exist!")
        return

    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)

    # Generate new files
    for i in range(existing_count + 1, total_ues + 1):
        # Generate filename
        new_filename = f"uecfg{i}.yaml"
        new_filepath = os.path.join(config_dir, new_filename)

        # Write new file
        with open(new_filepath, 'w') as f:
            yaml.dump(template, f, sort_keys=False)

        print_info(f"Created {new_filename}")

        # Generate and execute MongoDB commands
        insert_ue(i)
        print_success(f"MongoDB data inserted for UE {i}")

def check_upf_containers_running(num_upfs, timeout=60):
    """Check if all UPF containers are running"""
    client = docker.from_env()
    expected_upfs = num_upfs  # includes all UPFs (intermediate + PSA)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        running_upfs = 0
        try:
            containers = client.containers.list()
            for container in containers:
                if 'upf' in container.name.lower():
                    if container.status == 'running':
                        running_upfs += 1
            if running_upfs >= expected_upfs:
                return True
        except Exception as e:
            print_error(f"Error checking containers: {e}")
        
        time.sleep(5)
        print_info(f"Waiting for UPF containers to start... ({running_upfs}/{expected_upfs} running)")
    
    return False

def connect_ues(number):
    """Executes nr-ue inside the UERANSIM container for UE configs"""
    print_section("Connecting UEs")
    
    try:
        client = docker.from_env()
        container = next((c for c in client.containers.list() if 'ueransim' in c.name.lower()), None)

        if not container:
            print_error("UERANSIM container not running.")
            return

        # Check if UEs are already running
        ps_result = container.exec_run("ps aux | grep nr-ue")
        print_info(f"Current running UE processes:\n{ps_result.output.decode('utf-8')}")

        # Launch each UE with proper waiting time
        for i in range(1, number + 1):
            config_file = f"uecfg{i}.yaml"
            cmd = f"./nr-ue -c /ueransim/config/ue/{config_file}"
            print_info(f"Executing in container: {cmd}")
            
            # Execute the command and wait for it to complete
            exec_result = container.exec_run(cmd, detach=True, workdir="/ueransim")
            exec_id = exec_result.id if hasattr(exec_result, 'id') else 'unknown'
            print_success(f"Started UE with config {config_file}, Exec ID: {exec_id}")
            
            # Wait a moment to ensure the UE has time to initialize
            time.sleep(2)
            
    except docker.errors.DockerException as e:
        print_error(f"Error executing UE commands in UERANSIM: {e}")

def measure_traffic_option():
    """Option to measure traffic between containers with default container names"""
    print_section("Traffic Measurement Setup")
    
    measure = get_user_input("Do you want to measure traffic between containers? (y/n)", default="n")
    if measure.lower() != 'y':
        return

    # Use default container names
    client = "ueransim"
    server = "psa-upf"
    
    print_info(f"Using default containers - Client: {client}, Server: {server}")
    
    packet_count = get_user_input("Number of packets to send", default="10", is_int=True, min_value=1)
    packet_size = get_user_input("Packet size in bytes", default="100", is_int=True, min_value=1)
    interval = float(get_user_input("Interval between packets in seconds", default="1.0"))

    print_section(f"NETWORK METRICS TEST: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client: {client} | Server: {server}")
    print(f"Parameters: {packet_count} packets, {packet_size} bytes, {interval}s interval")

    measure_traffic_metrics(
        client,
        server,
        packet_size=packet_size,
        packet_count=packet_count,
        interval=interval,
    )


#########################################################################
#--------------
#########################################################################

def handle_upf_topology():
    """Handle UPF topology configuration"""
    print_section("UPF Topology Configuration")
    
    num_upfs = get_user_input("Enter total number of UPFs (including PSA-UPF)", default="2", is_int=True, min_value=2)
    edge_upfs = 1

    # Set up config output directory
    custom_config_dir = "./config/custom"
    os.makedirs(custom_config_dir, exist_ok=True)

    # Generate UPF configuration files
    print_info("Generating UPF configuration files...")
    for i in range(1, num_upfs):
        hostname = f"i-upf{i}" if i > 1 else "i-upf"
        is_edge = i <= edge_upfs
        upf_config = generate_upf_config(hostname, is_edge=is_edge)

        with open(os.path.join(custom_config_dir, f"upfcfg-{hostname}.yaml"), "w") as f:
            yaml.dump(upf_config, f, default_flow_style=False)
        print_success(f"Generated {hostname} configuration")

    # Generate PSA-UPF configuration
    psa_config = generate_upf_config("psa-upf", is_psa=True)
    with open(os.path.join(custom_config_dir, "upfcfg-psa-upf.yaml"), "w") as f:
        yaml.dump(psa_config, f, default_flow_style=False)
    print_success("Generated PSA-UPF configuration")

    # Generate SMF configuration
    print_info("Generating SMF configuration...")
    smf_config = generate_smf_config(num_upfs, edge_upfs)
    with open(os.path.join(custom_config_dir, "smfcfg.yaml"), "w") as f:
        yaml.dump(smf_config, f, default_flow_style=False)
    print_success("Generated SMF configuration")

    # Generate UE routing configuration
    print_info("Generating UE routing configuration...")
    uerouting_config = generate_uerouting_config(num_upfs, edge_upfs)
    with open(os.path.join(custom_config_dir, "uerouting.yaml"), "w") as f:
        yaml.dump(uerouting_config, f, default_flow_style=False)
    print_success("Generated UE routing configuration")

    # Generate Docker Compose configuration
    print_info("Generating Docker Compose configuration...")
    docker_compose = generate_docker_compose(num_upfs, edge_upfs)
    with open("docker-compose-custom.yaml", "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False)
    print_success("Generated Docker Compose configuration")

    print_section("Configuration Summary")
    print_info(f"- {num_upfs - 1} intermediate UPF configs in {custom_config_dir}")
    print_info(f"- 1 PSA UPF config in {custom_config_dir}")
    print_info(f"- SMF config with UPF topology in {custom_config_dir}")
    print_info(f"- UE routing config in {custom_config_dir}")
    print_info(f"- Docker Compose file: ./docker-compose-custom.yaml")

    # Start the containers
    print_section("Starting Containers")
    start_containers = get_user_input("Do you want to start the containers now? (y/n)", default="y")
    
    if start_containers.lower() == 'y':
        try:
            print_info("Starting containers with docker-compose...")
            subprocess.run(["docker", "compose", "-f", "docker-compose-custom.yaml", "up", "-d"], check=True)
            print_success("Containers started in detached mode")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to start containers: {e}")
            return

        # Wait for UPF containers to start
        print_info("Waiting for all UPF containers to start...")
        if not check_upf_containers_running(num_upfs):
            print_error("Timeout waiting for UPF containers to start")
            return
        print_success("All UPF containers are running")

    
        ###########################----------------------------------#######################
        # Prompt for network configuration with path optimization
        print_section("Network Configuration and Path Optimization")
        
        # Get number of UEs and path length - single prompt only
        num_ues = get_user_input("Enter number of UEs", default="1", is_int=True, min_value=1)
        m = get_user_input("Enter number of UPFs each UE should pass through (m)", default="2", is_int=True, min_value=2, max_value=num_upfs)
        
        # Configure gNB
        print_info("Configure gNB coordinates:")
        gnb_x = float(get_user_input("Enter gNB x coordinate (latitude)", default="0.0"))
        gnb_y = float(get_user_input("Enter gNB y coordinate (longitude)", default="0.0"))
        gnb_pos = (gnb_x, gnb_y)
        print_success(f"gNB configured at: {gnb_pos}")
        
        # Configure UPF coordinates
        print_info("Enter geographic coordinates for each UPF:")
        upf_positions = {}
        
        for i in range(1, num_upfs):
            name = f"upf{i}"
            print(f"\n{Fore.YELLOW}UPF: {name}{Style.RESET_ALL}")
            x = float(get_user_input(f"Enter x (latitude) for {name}"))
            y = float(get_user_input(f"Enter y (longitude) for {name}"))
            upf_positions[name] = (x, y)
        
        # PSA-UPF coordinates
        print(f"\n{Fore.YELLOW}UPF: psa{Style.RESET_ALL}")
        psa_x = float(get_user_input("Enter x (latitude) for PSA-UPF"))
        psa_y = float(get_user_input("Enter y (longitude) for PSA-UPF"))
        psa_pos = (psa_x, psa_y)
        upf_positions["psa"] = psa_pos
        
        # Initialize network for path calculation
        print_section("Path Optimization")
        print_info("Calculating optimal UPF path...")
        
        # Import the UPFNetwork class from interface.py logic
        import math
        from collections import defaultdict
        import heapq
        
        class UPFNetwork:
            def __init__(self):
                self.graph = defaultdict(dict)
                self.upf_loads = defaultdict(int)
                self.upf_positions = {}
                self.psa_position = None
                self.psa_upf = "psa"
                self.edge_upfs = set()

            def add_upf(self, upf_id, position):
                self.upf_positions[upf_id] = position

            def set_psa(self, position):
                self.psa_position = position
                self.upf_positions[self.psa_upf] = position

            def connect_upfs(self, upf1, upf2):
                distance = math.dist(self.upf_positions[upf1], self.upf_positions[upf2])
                self.graph[upf1][upf2] = distance
                self.graph[upf2][upf1] = distance

            def constrained_dijkstra(self, start, end, exact_hops, alpha=1.0, beta=0.5):
                heap = []
                heapq.heappush(heap, (0, 1, start, [start]))

                while heap:
                    current_cost, current_len, current_node, path = heapq.heappop(heap)

                    if current_len == exact_hops:
                        if current_node == end:
                            return path, current_cost
                        continue

                    for neighbor, distance in self.graph[current_node].items():
                        if neighbor in path:
                            continue
                        if neighbor in self.edge_upfs and neighbor != end:
                            continue
                        new_path = path + [neighbor]
                        step_cost = alpha * distance + beta * self.upf_loads[neighbor]
                        new_cost = current_cost + step_cost
                        heapq.heappush(heap, (new_cost, current_len + 1, neighbor, new_path))

                raise ValueError(f"No valid path of exactly {exact_hops} nodes from {start} to {end}")
        
        def rename_upfs(network, edge_upfs):
            renamed_positions = {}
            renamed_loads = {}
            renamed_graph = defaultdict(dict)
            old_to_new = {}
            new_to_old = {}
            i = 1
            j = 1

            for upf in network.upf_positions:
                if upf == network.psa_upf:
                    new_name = "psa-upf"
                elif upf in edge_upfs:
                    new_name = f"edge-upf{i}" if i > 1 else "i-upf"
                    i += 1
                else:
                    new_name = f"i-upf{j}" if j > 1 else "i-upf"
                    j += 1
                old_to_new[upf] = new_name
                new_to_old[new_name] = upf

            # Update positions and loads
            for old, new in old_to_new.items():
                renamed_positions[new] = network.upf_positions[old]
                renamed_loads[new] = network.upf_loads[old]

            # Update graph
            for old_src, neighbors in network.graph.items():
                new_src = old_to_new[old_src]
                for old_dst, dist in neighbors.items():
                    new_dst = old_to_new[old_dst]
                    renamed_graph[new_src][new_dst] = dist

            # Apply changes to network
            network.upf_positions = renamed_positions
            network.upf_loads = renamed_loads
            network.graph = renamed_graph
            network.edge_upfs = {old_to_new[u] for u in edge_upfs}
            return old_to_new, new_to_old
        
        # Create network and add UPFs
        network = UPFNetwork()
        
        # Add all UPFs to network
        for upf_id, position in upf_positions.items():
            if upf_id == "psa":
                network.set_psa(position)
            else:
                network.add_upf(upf_id, position)
        
        # Connect all UPFs to each other (fully connected graph)
        all_upfs = list(network.upf_positions.keys())
        for i in range(len(all_upfs)):
            for j in range(i+1, len(all_upfs)):
                network.connect_upfs(all_upfs[i], all_upfs[j])
        
        # Find the closest UPF to gNB to serve as edge UPF
        min_distance = float('inf')
        edge_upf = None
        
        for upf_id, upf_pos in network.upf_positions.items():
            if upf_id == network.psa_upf:
                continue
            distance = math.dist(gnb_pos, upf_pos)
            if distance < min_distance:
                min_distance = distance
                edge_upf = upf_id
        
        print_success(f"Selected edge UPF: {edge_upf} (closest to gNB)")
        
        # Add load to the edge UPF
        network.upf_loads[edge_upf] += num_ues
        network.edge_upfs = {edge_upf}
        
        # Rename UPFs for configuration consistency
        old_to_new, new_to_old = rename_upfs(network, {edge_upf})
        renamed_edge_upf = old_to_new[edge_upf]
        
        # Calculate optimal path
        try:
            path, cost = network.constrained_dijkstra(renamed_edge_upf, "psa-upf", m, alpha=1.0, beta=0.5)
            
            # Update loads for UPFs in the path
            for upf in path[1:-1]:
                network.upf_loads[upf] += num_ues
            
            print_success(f"Optimal path found: {' -> '.join(path)}")
            print_info(f"Path cost: {cost:.2f}")
            
            # Update UPF path in configuration files
            try:
                from utils.upf_path_updater import update_upf_path
                smf_config_path = "./config/custom/smfcfg.yaml"
                uerouting_config_path = "./config/custom/uerouting.yaml"
                
                if update_upf_path(path, smf_config_path, uerouting_config_path):
                    print_success("UPF path updated in configuration files")
                else:
                    print_warning("Failed to update UPF path in configuration files")
            except ImportError:
                print_warning("UPF path updater not available")
            
        except ValueError as e:
            print_error(f"No valid path found: {e}")
            print_warning("Continuing with default configuration...")
            path = []
        
        # Prepare coordinates for distance-based shaping
        print_section("Distance-based Bandwidth Shaping")
        upf_coords = {}
        
        # Convert network positions to the format expected by apply_distance
        for upf_name, position in network.upf_positions.items():
            upf_coords[upf_name] = {"x": position[0], "y": position[1]}
        
        print_info("Applying distance-based bandwidth limits using tc...")
        apply_distance(upf_coords)
        print_success("Bandwidth shaping complete.")

#########################################################################
def handle_ue_generation():
    """Handle UE generation"""
    print_section("UE Configuration")
    
    num_ues = get_user_input("Enter number of UEs to generate", default="1", is_int=True, min_value=1)
    
    generate_ue_configs(num_ues)

    # Restart UERANSIM container
    try:
        client = docker.from_env()
        ueransim_container = next(
            (c for c in client.containers.list(all=True) if 'ueransim' in c.name.lower()), None)

        if ueransim_container:
            print_info(f"Restarting container {ueransim_container.name}...")
            ueransim_container.restart()
            print_success("UERANSIM restarted successfully.")
            time.sleep(5)  # Give it time to fully restart
            
            # Ask if user wants to connect UEs - use the requested number (not the +1)
            connect_ues_prompt = get_user_input("Do you want to connect the UEs now? (y/n)", default="y")
            if connect_ues_prompt.lower() == 'y':
                connect_ues(num_ues + 1)  # Connect all generated UEs including the extra one
        else:
            print_warning("UERANSIM container not found.")
    except docker.errors.DockerException as e:
        print_error(f"Error restarting UERANSIM: {e}")

    print_success(f"Generated {num_ues} UE configuration files")

def cleanup_ue_configs():
    """Clean up UE config files except uecfg1.yaml"""
    print_section("Cleaning up UE Configuration Files")
    
    cleanup = get_user_input("Do you want to clean up extra UE config files? (y/n)", default="n")
    if cleanup.lower() != 'y':
        return
    
    ue_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config/custom/ue')
    deleted_count = 0
    
    for filename in os.listdir(ue_dir):
        if filename.startswith("uecfg") and filename.endswith(".yaml") and filename != "uecfg1.yaml":
            filepath = os.path.join(ue_dir, filename)
            try:
                os.remove(filepath)
                deleted_count += 1
                print_info(f"Deleted: {filename}")
            except Exception as e:
                print_error(f"Failed to delete {filename}: {e}")
    
    print_success(f"Cleaned up {deleted_count} UE configuration files")

def main_menu():
    """Display the main menu and handle user choices"""
    while True:
        print_header()
        print(f"{Fore.CYAN}Main Menu:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Configure UPF Topology")
        print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Generate UE Configurations")
        print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Measure Traffic Between Containers")
        print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Clean Up UE Configuration Files")
        print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Exit")
        
        choice = get_user_input("\nEnter your choice", default="0", is_int=True, min_value=0, max_value=4)
        
        if choice == 0:
            print_info("Exiting the program. Goodbye!")
            break
        elif choice == 1:
            handle_upf_topology()
        elif choice == 2:
            handle_ue_generation()
        elif choice == 3:
            measure_traffic_option()
        elif choice == 4:
            cleanup_ue_configs()
        
        # Wait for user to press Enter before showing the menu again
        input(f"\n{Fore.CYAN}Press Enter to return to the main menu...{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print_info("\nProgram interrupted. Exiting...")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
