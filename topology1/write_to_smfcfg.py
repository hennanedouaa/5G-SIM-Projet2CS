# This scripts writes in smfcfg the specified number of configuration of gNB
import yaml
import os

def update_smfcfg_with_gnbs(nbr_gnb, yaml_path='~/free5gc-compose/config/custom-ue/smfcfg.yaml'):
    yaml_path = os.path.expanduser(yaml_path)

    # Load current YAML
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    # Navigate to the userplaneInformation
    up_nodes = config['configuration']['userplaneInformation']['upNodes']
    links = config['configuration']['userplaneInformation']['links']

    # Remove any existing gNB entries (optional, to avoid duplicates)
    up_nodes = {k: v for k, v in up_nodes.items() if not k.startswith('gNB')}

    # Add new gNB entries
    for i in range(1, nbr_gnb + 1):
        up_nodes[f'gNB{i}'] = {
            'type': 'AN',
            'nodeID': f'gnb{i}.free5gc.org'
        }

    # Remove old gNB links (optional cleanup)
    links = [link for link in links if not (link['A'].startswith('gNB') or link['B'].startswith('gNB'))]

    # Add new links from each gNB to I-UPF
    for i in range(1, nbr_gnb + 1):
        links.insert(0, {'A': f'gNB{i}', 'B': 'I-UPF'})

    # Update the config
    config['configuration']['userplaneInformation']['upNodes'] = up_nodes
    config['configuration']['userplaneInformation']['links'] = links

    # Write back the updated file
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, sort_keys=False)

    print(f"Updated smfcfg.yaml with {nbr_gnb} gNBs.")

if __name__ == '__main__':
 update_smfcfg_with_gnbs(3)
