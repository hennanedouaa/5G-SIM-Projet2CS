import sys
import subprocess
def generate_urllc_traffic(path_to_init_sh="~/free5gc-compose/init.sh"):
    try:
        # Running the init.sh script
        # the init.sh should be inside ~/free5gc-compose/ folder
        print(f"Running: {path_to_init_sh}")
        subprocess.run(["bash", path_to_init_sh], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

if __name__ == "__main__":
        if len(sys.argv) == 2:
            path_to_init_sh = sys.argv[1]
            generate_urllc_traffic(path_to_init_sh)
        else:
            generate_urllc_traffic()
