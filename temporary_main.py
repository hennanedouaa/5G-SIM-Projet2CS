#!/usr/bin/env python3
import sys
from utils.generate_free5gc_config import create_upf_topology

def main():
    # Check command line arguments
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <number_of_upfs>")
        print("Example: python3 demo_upf_topology.py 3")
        return 1
    
    try:
        num_upfs = int(sys.argv[1])
        if num_upfs < 1:
            raise ValueError("Number of UPFs must be at least 1")
            
        result = create_upf_topology(num_upfs)
        
        print("Successfully created UPF topology with the following files:")
        print(f"- Docker Compose: {result['docker_compose']}")
        for i, path in enumerate(result['upf_configs'], 1):
            print(f"- UPF{i} config: {path}")
        print(f"- SMF config: {result['smf_config']}")
        print(f"- UE Routing config: {result['uerouting_config']}")
        
    except ValueError as e:
        print(f"Error creating UPF topology: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
