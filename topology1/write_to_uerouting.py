# This script writes into uerouting.yaml:
# UE groupings: each group of UEs and their corresponding UPF path

import yaml
import os

class InlineList(list):
    """A list that should be dumped inline in YAML."""
    pass

def inline_list_representer(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

yaml.add_representer(InlineList, inline_list_representer)

def overwrite_ue_routing(distribution, yaml_path='~/free5gc-compose/config/custom-ue/uerouting.yaml'):
    yaml_path = os.path.expanduser(yaml_path)

    # Load existing YAML content
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    # Build new ueRoutingInfo
    new_ue_info = {}
    base_imsi = 208930000000001
    ue_counter = 1

    for gnb_index, num_ues in enumerate(distribution, start=1):
        for _ in range(num_ues):
            ue_name = f'UE{ue_counter}'
            imsi = f'imsi-{base_imsi + ue_counter - 1}'
            new_ue_info[ue_name] = {
                'members': [imsi],
                'topology': [
                    {'A': f'gNB{gnb_index}', 'B': 'I-UPF'},
                    {'A': 'I-UPF', 'B': 'I-UPF2'},
                    {'A': 'I-UPF2', 'B': 'PSA-UPF'}
                ],
                'specificPath': [
                    {'dest': '1.0.0.1/32', 'path': InlineList(['I-UPF', 'I-UPF2', 'PSA-UPF'])}
                ]
            }
            ue_counter += 1

    config['ueRoutingInfo'] = new_ue_info

    # Dump YAML
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, sort_keys=False)

    print(f"ueRoutingInfo overwritten in {yaml_path}")

if __name__ == '__main__':
 overwrite_ue_routing([2, 1, 3])
