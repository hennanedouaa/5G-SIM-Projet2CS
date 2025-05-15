# This file is reponsible for creating configuration of UE and put it in the OUTPUT_DIR
import yaml
import sys
import os

# Constants
BASE_FILE = "/home/user/free5gc-compose/config/uecfg-ulcl.yaml"
OUTPUT_DIR = "/home/user/free5gc-compose/config/custom-ue-ueransim/generated_configs"
BASE_IMSI_NUM = 208930000000001  # numeric form of the IMSI in the base file

def generate_configs(n):
    # Create output directory if not exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load base config
    with open(BASE_FILE, 'r') as f:
        base_config = yaml.safe_load(f)

    for i in range(n):
        new_config = base_config.copy()
        new_imsi_num = BASE_IMSI_NUM + i
        new_imsi = f"imsi-{new_imsi_num:015d}"
        new_config["supi"] = new_imsi

        out_filename = f"{OUTPUT_DIR}/uecfg-{i+1:03}.yaml"
        with open(out_filename, 'w') as out_file:
            yaml.dump(new_config, out_file, sort_keys=False)

        print(f"Generated: {out_filename} with IMSI {new_imsi}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_uecfgs.py <N>")
        sys.exit(1)

    try:
        N = int(sys.argv[1])
        generate_configs(N)
    except ValueError:
        print("Please provide a valid integer.")
