import json
import subprocess
import re

def get_upfs_with_ips():
    """
    Returns a JSON list of all UPF containers with their IP addresses.
    
    Returns:
        str: JSON string containing list of UPF containers with their IPs
        Format: [{"name": "upf-1", "ip": "10.100.200.2"}, ...]
    """
    try:
        # Get all container IDs
        container_ids = subprocess.check_output(['docker', 'ps', '-q']).decode().strip().split()
        
        upfs = []
        
        for cid in container_ids:
            # Get container name and IP
            inspect_output = subprocess.check_output(
                ['docker', 'inspect', '-f', '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', cid]
            ).decode().strip()
            
            # Parse the output (format: "/container_name - ip_address")
            match = re.match(r'^/(.+?) - (\d+\.\d+\.\d+\.\d+)$', inspect_output)
            if match:
                name, ip = match.groups()
                # Filter for UPF containers (names starting with 'upf-')
                if name.startswith('upf-'):
                    upfs.append({
                        'name': name,
                        'ip': ip
                    })
        
        return json.dumps(upfs, indent=2)
    
    except subprocess.CalledProcessError as e:
        return json.dumps({'error': f'Docker command failed: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': str(e)})

# Example usage:
if __name__ == "__main__":
    upfs_json = get_upfs_with_ips()
    print(upfs_json)