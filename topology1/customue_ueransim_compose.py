# This file is responsible for writing the UE configuration into docker compose file.
# More specifically: under services/ueransim/volumes
import os
import yaml

compose_path = "/home/user/free5gc-compose/docker-compose-ulcl-3.yaml"
generated_dir = "/home/user/free5gc-compose/config/custom-ue-ueransim/generated_configs"
container_mount = "/ueransim/config"

# Load existing docker-compose file
with open(compose_path, "r") as f:
    docker_compose = yaml.safe_load(f)

# Get the ueransim service
ueransim_service = docker_compose['services']['ueransim']

# Ensure 'volumes' exists
if 'volumes' not in ueransim_service:
    ueransim_service['volumes'] = []

# Add generated config files to volumes
for filename in sorted(os.listdir(generated_dir)):
    if filename.endswith(".yaml"):
        host_path = os.path.join(generated_dir, filename)
        container_path = os.path.join(container_mount, filename)
        volume_entry = f"{host_path}:{container_path}"

        # Add only if not already present
        if volume_entry not in ueransim_service['volumes']:
            ueransim_service['volumes'].append(volume_entry)

# Save updated docker-compose file (backup first)
backup_path = compose_path + ".bak"
os.rename(compose_path, backup_path)

with open(compose_path, "w") as f:
    yaml.dump(docker_compose, f, sort_keys=False)

print(f"Updated {compose_path} and saved backup as {backup_path}")
