# Copy ULCL/ into ULCL-custom/
# Update smfcfg.yaml links.
# Update uerouting 'links' attribute.
# Update uerouting 'path' attribute.

import os
import shutil
import yaml
from pathlib import Path
import re
def copy_ulcl_folder():
    """Copy ULCL folder to ULCL-custom, overwriting if exists"""
    try:
        source = "./config/ULCL"
        destination = "config/ULCL-custom"

        if os.path.exists(destination):
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        print(f"Copied {source}/ to {destination}/")
    except Exception as e:
        print(f"Error copying folder: {e}")
        raise

def parse_upf_order():
    """Parse upf_path.txt and return ordered UPF list"""
    upf_order = []
    try:
        with open("upf_path.txt", 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) == 2:
                    upf_order.append(f"I-{parts[1].upper()}")
        print(f"Parsed UPF order: {upf_order}")
        return upf_order
    except Exception as e:
        print(f"Error parsing UPF order: {e}")
        raise

def update_links(upf_order, config_file):
    """Update links in ULCL-custom/{config_file}.yaml by replacing old links with new chain"""
    config_path = f'./config/ULCL-custom/{config_file}'
    try:
        new_links = []
        # Initial hop gNB1 -> first UPF 
        new_links.append({"A": "gNB1", "B":upf_order[0]})
        # Intermediate hops
        for i in range(len(upf_order) - 1):
            new_links.append({"A": upf_order[i], "B": upf_order[i + 1]})
        new_links.append({"A": upf_order[-1], "B": "PSA-UPF"})

        # Read existing config
        with open(config_path, 'r') as f:
            content = f.read()
        
	# Generate the new links section with proper indentation
        new_section = ""
        for link in new_links:
            new_section += f"      - A: {link['A']}\n"
       	    new_section += f"        B: {link['B']}\n" 
        pattern = r'(      - A: .*\n        B: .*\n)+'

        updated_content = re.sub(pattern, new_section, content)
        # Write back to file
        with open(config_path, 'w') as f:
            f.write(updated_content)

        print(f"Successfully replaced links in {config_path}")
    except Exception as e:
        print(f"Failed to update SMF config: {e}")
        raise

def update_path(upf_order: list[str], yaml_file: str) -> None:
    """
    Updates the 'path:' attribute in a YAML file with the given UPF order,
    adding PSA-UPF at the end and maintaining proper YAML list format.
    
    Args:
        yaml_file: Path to the YAML file
        upf_order: List of UPF nodes (e.g., ["I-UPF2", "I-UPF1"])
    """
    try:
        # Read the YAML file
        with open(f'./config/ULCL-custom/{yaml_file}', 'r') as f:
            content = f.read()
        
        # Create the new path value with PSA-UPF at the end
        new_path = upf_order + ["PSA-UPF"]
        
        # Convert to properly formatted YAML list string
        # This will look like: [I-UPF2, I-UPF3, PSA-UPF]
        new_path_str = "[" + ", ".join(new_path) + "]"
        print("New path: ", new_path_str)
        # Use regex to find and replace the path attribute
        # Pattern matches: "path:" followed by optional spaces and the existing list
        pattern = r'path:\s*\[.*\]'
        path_match = re.search(pattern, content)
        print("Changing: ", path_match)
        updated_content = re.sub(pattern, f"path: {new_path_str}", content)
        
        # Write back to the file
        with open(f'./config/ULCL-custom/{yaml_file}', 'w') as f:
            f.write(updated_content)
            
        print(f"Updated {yaml_file} with path: {new_path_str}")
        
    except Exception as e:
        print(f"Error updating YAML file: {e}")
        raise
def main():
    print("Starting 5G UPF configuration update...")
    
    # 1. Copy ULCL folder
    copy_ulcl_folder()
    
    # 2. Parse UPF order
    upf_order = parse_upf_order()
    
    # 3. Update SMF config
    update_links(upf_order, "smfcfg.yaml")
    
    # 4. Update uerouting.yaml
    update_links(upf_order, "uerouting.yaml") 
    
    # 5. Update path
    update_path(upf_order, "uerouting.yaml")
    print("All tasks completed successfully!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Script failed: {e}")
        exit(1)
