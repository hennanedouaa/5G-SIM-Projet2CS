#!/usr/bin/env python3
"""
Free5GC UPF Path Updater
------------------------
This script updates existing Free5GC configuration files to modify the UPF path
according to a specified list of UPF names.

It updates:
1. SMF configuration - links section
2. UE routing configuration - topology and specificPath sections
"""

import yaml
import os
import sys
from pathlib import Path


def update_upf_path(upf_path_list, smf_config_path, uerouting_config_path):
    """
    Update SMF and UE routing configurations with a new UPF path.

    Parameters:
    - upf_path_list: List of UPF names in order (e.g., ["I-UPF", "I-UPF3", "I-UPF4", "PSA-UPF"])
    - smf_config_path: Path to SMF configuration file
    - uerouting_config_path: Path to UE routing configuration file
    """
    # Validate input
    if not upf_path_list or len(upf_path_list) < 2:
        print("Error: UPF path list must contain at least two UPFs")
        return False
    
    if "psa" not in upf_path_list:
        print("Warning: UPF path should typically include PSA-UPF")
    
    # Load existing configurations
    try:
        with open(smf_config_path, 'r') as file:
            smf_config = yaml.safe_load(file)
        
        with open(uerouting_config_path, 'r') as file:
            uerouting_config = yaml.safe_load(file)
    except FileNotFoundError as e:
        print(f"Error: Configuration file not found - {e}")
        return False
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in configuration file - {e}")
        return False
    
    # Update SMF links section
    # First, find 'gNB1' in node list to include it in the path
    gnb_found = "gNB1" in smf_config["configuration"]["userplaneInformation"]["upNodes"]
    
    # Create new links array
    new_links = []
    
    # Add link from gNB to first UPF if gNB exists
    if gnb_found:
        new_links.append({
            "A": "gNB1",
            "B": upf_path_list[0]
        })
    
    # Create links between UPFs in the specified order
    for i in range(len(upf_path_list) - 1):
        new_links.append({
            "A": upf_path_list[i],
            "B": upf_path_list[i + 1]
        })
    
    # Update SMF links
    smf_config["configuration"]["userplaneInformation"]["links"] = new_links
    
    # Update UE routing topology and specificPath for all UEs
    for ue_key, ue_info in uerouting_config["ueRoutingInfo"].items():
        # Create new topology based on UPF path
        new_topology = []
        
        # Add gNB to first UPF link if applicable
        if gnb_found:
            new_topology.append({
                "A": "gNB1", 
                "B": upf_path_list[0]
            })
        
        # Add UPF to UPF links
        for i in range(len(upf_path_list) - 1):
            new_topology.append({
                "A": upf_path_list[i],
                "B": upf_path_list[i + 1]
            })
        
        # Update topology for this UE
        ue_info["topology"] = new_topology
        
        # Update specific paths for this UE if they exist
        if "specificPath" in ue_info:
            for path_entry in ue_info["specificPath"]:
                path_entry["path"] = upf_path_list
    
    # Save updated configurations
    try:
        with open(smf_config_path, 'w') as file:
            yaml.dump(smf_config, file, default_flow_style=False)
        
        with open(uerouting_config_path, 'w') as file:
            yaml.dump(uerouting_config, file, default_flow_style=False)
        
        print(f"Successfully updated UPF path to: {' -> '.join(upf_path_list)}")
        if gnb_found:
            print(f"Path including gNB: gNB1 -> {' -> '.join(upf_path_list)}")
        return True
    
    except Exception as e:
        print(f"Error saving configuration files: {e}")
        return False



