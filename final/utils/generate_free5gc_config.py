#!/usr/bin/env python3
import sys
import yaml
import os
import copy
import ipaddress

def generate_docker_compose(num_upfs):
    """
    Generate a Docker Compose configuration for Free5GC with a variable number of UPFs.
    
    Args:
        num_upfs (int): Number of UPF instances to create
        
    Returns:
        dict: Docker Compose configuration
    """
    
    # Base configuration
    docker_compose = {
        "version": "3.8",
        "services": {},
        "networks": {
            "privnet": {
                "ipam": {
                    "driver": "default",
                    "config": [{"subnet": "10.100.200.0/24"}]
                },
                "driver_opts": {
                    "com.docker.network.bridge.name": "br-free5gc"
                }
            }
        },
        "volumes": {
            "dbdata": {}
        }
    }
    
    # Generate UPF services
    for i in range(1, num_upfs + 1):
        upf_service_name = f"free5gc-upf-{i}"
        container_name = f"upf-{i}"
        
        docker_compose["services"][upf_service_name] = {
            "container_name": container_name,
            "image": "free5gc/upf:v4.0.0",
            "command": "bash -c \"./upf-iptables.sh && ./upf -c ./config/upfcfg.yaml\"",
            "volumes": [
                f"./config/multiUPF/upf{i}cfg.yaml:/free5gc/config/upfcfg.yaml",
                "./config/upf-iptables.sh:/free5gc/upf-iptables.sh"
            ],
            "cap_add": ["NET_ADMIN"],
            "networks": {
                "privnet": {
                    "aliases": [f"upf{i}.free5gc.org"]
                }
            }
        }
    
    # Add other standard services
    docker_compose["services"].update({
        "db": {
            "container_name": "mongodb",
            "image": "mongo:3.6.8",
            "command": "mongod --port 27017",
            "expose": ["27017"],
            "volumes": ["dbdata:/data/db"],
            "networks": {
                "privnet": {
                    "aliases": ["db"]
                }
            }
        },
        "free5gc-nrf": {
            "container_name": "nrf",
            "image": "free5gc/nrf:v4.0.0",
            "command": "./nrf -c ./config/nrfcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/nrfcfg.yaml:/free5gc/config/nrfcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "DB_URI": "mongodb://db/free5gc",
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["nrf.free5gc.org"]
                }
            },
            "depends_on": ["db"]
        },
        "free5gc-amf": {
            "container_name": "amf",
            "image": "free5gc/amf:v4.0.0",
            "command": "./amf -c ./config/amfcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/amfcfg.yaml:/free5gc/config/amfcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "ipv4_address": "10.100.200.16",
                    "aliases": ["amf.free5gc.org"]
                }
            },
            "depends_on": ["free5gc-nrf"]
        },
        "free5gc-ausf": {
            "container_name": "ausf",
            "image": "free5gc/ausf:v4.0.0",
            "command": "./ausf -c ./config/ausfcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/ausfcfg.yaml:/free5gc/config/ausfcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["ausf.free5gc.org"]
                }
            },
            "depends_on": ["free5gc-nrf"]
        },
        "free5gc-nssf": {
            "container_name": "nssf",
            "image": "free5gc/nssf:v4.0.0",
            "command": "./nssf -c ./config/nssfcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/nssfcfg.yaml:/free5gc/config/nssfcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["nssf.free5gc.org"]
                }
            },
            "depends_on": ["free5gc-nrf"]
        },
        "free5gc-pcf": {
            "container_name": "pcf",
            "image": "free5gc/pcf:v4.0.0",
            "command": "./pcf -c ./config/pcfcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/pcfcfg.yaml:/free5gc/config/pcfcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["pcf.free5gc.org"]
                }
            },
            "depends_on": ["free5gc-nrf"]
        }
    })
    
    # Create SMF service with dynamic dependencies on UPFs
    upf_depends = ["free5gc-nrf"]
    for i in range(1, num_upfs + 1):
        upf_depends.append(f"free5gc-upf-{i}")
    
    docker_compose["services"]["free5gc-smf"] = {
        "container_name": "smf",
        "image": "free5gc/smf:v4.0.0",
        "command": "./smf -c ./config/smfcfg.yaml -u ./config/uerouting.yaml",
        "expose": ["8000"],
        "volumes": [
            "./config/multiUPF/smf-multi-cfg.yaml:/free5gc/config/smfcfg.yaml",
            "./config/multiUPF/uerouting-multi.yaml:/free5gc/config/uerouting.yaml",
            "./cert:/free5gc/cert"
        ],
        "environment": {
            "GIN_MODE": "release"
        },
        "networks": {
            "privnet": {
                "aliases": ["smf.free5gc.org"]
            }
        },
        "depends_on": upf_depends
    }
    
    # Add remaining services
    docker_compose["services"].update({
        "free5gc-udm": {
            "container_name": "udm",
            "image": "free5gc/udm:v4.0.0",
            "command": "./udm -c ./config/udmcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/udmcfg.yaml:/free5gc/config/udmcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["udm.free5gc.org"]
                }
            },
            "depends_on": ["db", "free5gc-nrf"]
        },
        "free5gc-udr": {
            "container_name": "udr",
            "image": "free5gc/udr:v4.0.0",
            "command": "./udr -c ./config/udrcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/udrcfg.yaml:/free5gc/config/udrcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "DB_URI": "mongodb://db/free5gc",
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["udr.free5gc.org"]
                }
            },
            "depends_on": ["db", "free5gc-nrf"]
        },
        "free5gc-webui": {
            "container_name": "webui",
            "image": "free5gc/webui:v4.0.0",
            "command": "./webui -c ./config/webuicfg.yaml",
            "expose": ["2121"],
            "volumes": [
                "./config/webuicfg.yaml:/free5gc/config/webuicfg.yaml"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["webui"]
                }
            },
            "ports": ["5000:5000", "2122:2122", "2121:2121"],
            "depends_on": ["db", "free5gc-nrf"]
        },
        "free5gc-chf": {
            "container_name": "chf",
            "image": "free5gc/chf:v4.0.0",
            "command": "./chf -c ./config/chfcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/chfcfg.yaml:/free5gc/config/chfcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "DB_URI": "mongodb://db/free5gc",
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["chf.free5gc.org"]
                }
            },
            "depends_on": ["db", "free5gc-nrf", "free5gc-webui"]
        }
    })
    
    # Create n3iwf service with dynamic dependencies on UPFs
    n3iwf_depends = ["free5gc-amf", "free5gc-smf"]
    for i in range(1, num_upfs + 1):
        n3iwf_depends.append(f"free5gc-upf-{i}")
    
    docker_compose["services"]["free5gc-n3iwf"] = {
        "container_name": "n3iwf",
        "image": "free5gc/n3iwf:v4.0.0",
        "command": "./n3iwf -c ./config/n3iwfcfg.yaml",
        "volumes": [
            "./config/n3iwfcfg.yaml:/free5gc/config/n3iwfcfg.yaml",
            "./config/n3iwf-ipsec.sh:/free5gc/n3iwf-ipsec.sh"
        ],
        "environment": {
            "GIN_MODE": "release"
        },
        "cap_add": ["NET_ADMIN"],
        "networks": {
            "privnet": {
                "ipv4_address": "10.100.200.15",
                "aliases": ["n3iwf.free5gc.org"]
            }
        },
        "depends_on": n3iwf_depends
    }
    
    # Create tngf service with dynamic dependencies on UPFs
    tngf_depends = ["free5gc-amf", "free5gc-smf"]
    for i in range(1, num_upfs + 1):
        tngf_depends.append(f"free5gc-upf-{i}")
    
    docker_compose["services"]["free5gc-tngf"] = {
        "container_name": "tngf",
        "image": "free5gc/tngf:latest",
        "command": "./tngf -c ./config/tngfcfg.yaml",
        "volumes": [
            "./config/tngfcfg.yaml:/free5gc/config/tngfcfg.yaml",
            "./cert:/free5gc/cert"
        ],
        "environment": {
            "GIN_MODE": "release"
        },
        "cap_add": ["NET_ADMIN"],
        "network_mode": "host",
        "depends_on": tngf_depends
    }
    
    # Add remaining services
    docker_compose["services"].update({
        "free5gc-nef": {
            "container_name": "nef",
            "image": "free5gc/nef:latest",
            "command": "./nef -c ./config/nefcfg.yaml",
            "expose": ["8000"],
            "volumes": [
                "./config/nefcfg.yaml:/free5gc/config/nefcfg.yaml",
                "./cert:/free5gc/cert"
            ],
            "environment": {
                "GIN_MODE": "release"
            },
            "networks": {
                "privnet": {
                    "aliases": ["nef.free5gc.org"]
                }
            },
            "depends_on": ["db", "free5gc-nrf"]
        }
    })
    
    # Create ueransim service with dynamic dependencies on UPFs
    ueransim_depends = ["free5gc-amf"]
    for i in range(1, num_upfs + 1):
        ueransim_depends.append(f"free5gc-upf-{i}")
    
    docker_compose["services"]["ueransim"] = {
        "container_name": "ueransim",
        "image": "free5gc/ueransim:latest",
        "command": "./nr-gnb -c ./config/gnbcfg.yaml",
        "volumes": [
            "./config/gnbcfg.yaml:/ueransim/config/gnbcfg.yaml",
            "./config/uecfg-multi.yaml:/ueransim/config/uecfg.yaml"
        ],
        "cap_add": ["NET_ADMIN"],
        "devices": ["/dev/net/tun"],
        "networks": {
            "privnet": {
                "aliases": ["gnb.free5gc.org"]
            }
        },
        "depends_on": ueransim_depends
    }
    
    # Add n3iwue service
    docker_compose["services"]["n3iwue"] = {
        "container_name": "n3iwue",
        "image": "free5gc/n3iwue:latest",
        "command": "bash -c \"ip route del default && ip route add default via 10.100.200.1 dev eth0 metric 203 && sleep infinity\"",
        "volumes": [
            "./config/n3uecfg.yaml:/n3iwue/config/n3ue.yaml"
        ],
        "cap_add": ["NET_ADMIN"],
        "devices": ["/dev/net/tun"],
        "networks": {
            "privnet": {
                "ipv4_address": "10.100.200.203",
                "aliases": ["n3ue.free5gc.org"]
            }
        },
        "depends_on": ["free5gc-n3iwf"]
    }
    
    return docker_compose

def generate_upf_config(upf_num, total_upfs):
    """
    Generate UPF configuration YAML for a specific UPF
    
    Args:
        upf_num (int): The UPF number (1-based index)
        total_upfs (int): Total number of UPFs in the setup
        
    Returns:
        dict: UPF configuration
    """
    # Base CIDR blocks for UPFs (starting from UPF1)
    base_cidr = 60 + upf_num
    
    # Create basic config
    upf_config = {
        "version": "1.0.3",
        "description": f"UPF{upf_num} {'final' if upf_num == total_upfs else 'intermediate'} local configuration",
        
        "pfcp": {
            "addr": f"upf{upf_num}.free5gc.org",
            "nodeID": f"upf{upf_num}.free5gc.org",
            "retransTimeout": "1s",
            "maxRetrans": 3
        },
        
        "gtpu": {
            "forwarder": "gtp5g",
            "ifList": []
        },
        
        "dnnList": [
            {
                "dnn": "internet",
                "cidr": f"10.{base_cidr}.0.0/16"
            }
        ],
        
        "logger": {
            "enable": True,
            "level": "info",
            "reportCaller": False
        }
    }
    
    # Configure interface list based on UPF position
    if upf_num == 1:
        # First UPF connects to gNB (N3) and next UPF (N9)
        upf_config["gtpu"]["ifList"] = [
            {
                "addr": f"upf{upf_num}.free5gc.org",
                "type": "N3"
            }
        ]
        
        # Add N9 interface if there are more UPFs
        if total_upfs > 1:
            upf_config["gtpu"]["ifList"].append({
                "addr": f"upf{upf_num}.free5gc.org",
                "type": "N9"
            })
    
    elif upf_num == total_upfs:
        # Last UPF only needs N9 from previous UPF
        upf_config["gtpu"]["ifList"] = [
            {
                "addr": f"upf{upf_num}.free5gc.org",
                "type": "N9"
            }
        ]
    
    else:
        # Middle UPFs have N9 interfaces for both previous and next UPF
        upf_config["gtpu"]["ifList"] = [
            {
                "addr": f"upf{upf_num}.free5gc.org",
                "type": "N9"
            }
        ]
    
    return upf_config

def generate_smf_config(num_upfs):
    """
    Generate SMF configuration YAML for multiple UPFs
    
    Args:
        num_upfs (int): Total number of UPFs
        
    Returns:
        dict: SMF configuration
    """
    # Base SMF configuration (from template)
    smf_config = {
        "info": {
            "version": "1.0.7",
            "description": "SMF initial local configuration"
        },
        "configuration": {
            "smfName": "SMF",
            "sbi": {
                "scheme": "http",
                "registerIPv4": "smf.free5gc.org",
                "bindingIPv4": "smf.free5gc.org",
                "port": 8000,
                "tls": {
                    "key": "cert/smf.key",
                    "pem": "cert/smf.pem"
                }
            },
            "serviceNameList": [
                "nsmf-pdusession",
                "nsmf-event-exposure",
                "nsmf-oam"
            ],
            "snssaiInfos": [
                {
                    "sNssai": {
                        "sst": 1,
                        "sd": "010203"
                    },
                    "dnnInfos": [
                        {
                            "dnn": "internet",
                            "dns": {
                                "ipv4": "8.8.8.8",
                                "ipv6": "2001:4860:4860::8888"
                            }
                        }
                    ]
                },
                {
                    "sNssai": {
                        "sst": 1,
                        "sd": "112233"
                    },
                    "dnnInfos": [
                        {
                            "dnn": "internet",
                            "dns": {
                                "ipv4": "8.8.8.8",
                                "ipv6": "2001:4860:4860::8888"
                            }
                        }
                    ]
                }
            ],
            "plmnList": [
                {
                    "mcc": "208",
                    "mnc": "93"
                }
            ],
            "locality": "area1",
            "pfcp": {
                "nodeID": "smf.free5gc.org",
                "listenAddr": "smf.free5gc.org",
                "externalAddr": "smf.free5gc.org",
                "heartbeatInterval": "5s"
            },
            "userplaneInformation": {
                "upNodes": {
                    "gNB1": {
                        "type": "AN",
                        "nodeID": "gnb.free5gc.org"
                    }
                },
                "links": []
            },
            "t3591": {
                "enable": True,
                "expireTime": "16s",
                "maxRetryTimes": 3
            },
            "t3592": {
                "enable": True,
                "expireTime": "16s",
                "maxRetryTimes": 3
            },
            "nrfUri": "http://nrf.free5gc.org:8000",
            "nrfCertPem": "cert/nrf.pem",
            "urrPeriod": 10,
            "urrThreshold": 1000,
            "requestedUnit": 1000
        },
        "logger": {
            "enable": True,
            "level": "info",
            "reportCaller": False
        }
    }
    
    # Add UPF nodes
    for i in range(1, num_upfs + 1):
        base_cidr = 60 + i
        
        upf_node = {
            "type": "UPF",
            "nodeID": f"upf{i}.free5gc.org",
            "sNssaiUpfInfos": [
                {
                    "sNssai": {
                        "sst": 1,
                        "sd": "010203"
                    },
                    "dnnUpfInfoList": [
                        {
                            "dnn": "internet",
                            "pools": [
                                {"cidr": f"10.{base_cidr}.0.0/16"}
                            ],
                            "staticPools": [
                                {"cidr": f"10.{base_cidr}.100.0/24"}
                            ]
                        }
                    ]
                }
            ],
            "interfaces": []
        }
        
        # Configure interfaces based on UPF position
        if i == 1:
            # First UPF has N3 (from gNB) and potentially N9 (to next UPF)
            upf_node["interfaces"] = [
                {
                    "interfaceType": "N3",
                    "endpoints": [f"upf{i}.free5gc.org"],
                    "networkInstances": ["internet"]
                }
            ]
            
            if num_upfs > 1:
                upf_node["interfaces"].append({
                    "interfaceType": "N9",
                    "endpoints": [f"upf{i}.free5gc.org"],
                    "networkInstances": ["internet"]
                })
        else:
            # Other UPFs only have N9
            upf_node["interfaces"] = [
                {
                    "interfaceType": "N9",
                    "endpoints": [f"upf{i}.free5gc.org"],
                    "networkInstances": ["internet"]
                }
            ]
            
        # Add UPF node to SMF config
        smf_config["configuration"]["userplaneInformation"]["upNodes"][f"UPF{i}"] = upf_node
    
    # Configure links between nodes
    # First link: gNB1 to UPF1
    smf_config["configuration"]["userplaneInformation"]["links"].append({
        "A": "gNB1",
        "B": "UPF1"
    })
    
    # Links between UPFs
    for i in range(1, num_upfs):
        smf_config["configuration"]["userplaneInformation"]["links"].append({
            "A": f"UPF{i}",
            "B": f"UPF{i+1}"
        })
    
    return smf_config

def generate_uerouting_config(num_upfs):
    """
    Generate UE routing configuration YAML for multiple UPFs
    
    Args:
        num_upfs (int): Total number of UPFs
        
    Returns:
        dict: UE routing configuration
    """
    # Base UE routing configuration
    uerouting_config = {
        "info": {
            "version": "1.0.7",
            "description": "Routing information for UE"
        },
        "ueRoutingInfo": {
            "UE1": {
                "members": ["imsi-208930000000001"],
                "topology": [],
                "specificPath": []
            }
        },
        "routeProfile": {
            "MEC1": {
                "forwardingPolicyID": 10
            }
        },
        "pfdDataForApp": [
            {
                "applicationId": "edge",
                "pfds": [
                    {
                        "pfdID": "pfd1",
                        "flowDescriptions": ["permit out ip from 10.60.0.1 8080 to any"]
                    }
                ]
            }
        ]
    }
    
    # Configure default topology
    # First link: gNB1 to UPF1
    uerouting_config["ueRoutingInfo"]["UE1"]["topology"].append({
        "A": "gNB1",
        "B": "UPF1"
    })
    
    # Links between UPFs
    for i in range(1, num_upfs):
        uerouting_config["ueRoutingInfo"]["UE1"]["topology"].append({
            "A": f"UPF{i}",
            "B": f"UPF{i+1}"
        })
    
    # Add specific path examples
    base_cidr = 60  # Last UPF CIDR
    uerouting_config["ueRoutingInfo"]["UE1"]["specificPath"].append({
        "dest": f"10.{base_cidr}.0.103/32",
        "path": [f"UPF{i}" for i in range(1, num_upfs + 1)]
    })
    
    return uerouting_config

def ensure_directory(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_upf_topology(num_upfs):
    """
    Create a complete UPF topology with all necessary configurations.
    
    Args:
        num_upfs (int): Number of UPFs to create in the topology
        
    Returns:
        dict: Dictionary containing paths to all generated files
    """
    if num_upfs < 1:
        raise ValueError("Number of UPFs must be at least 1")
    
    # Create necessary directories
    ensure_directory("config")
    ensure_directory("config/multiUPF")
    
    # Define custom representer for proper formatting
    def represent_str_with_style(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    
    yaml.add_representer(str, represent_str_with_style)
    
    # Generate Docker Compose file
    docker_compose = generate_docker_compose(num_upfs)
    docker_compose_path = "docker-compose.yaml"
    with open(docker_compose_path, "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False, sort_keys=False)
    
    # Generate UPF configurations
    upf_config_paths = []
    for i in range(1, num_upfs + 1):
        upf_config = generate_upf_config(i, num_upfs)
        path = f"config/multiUPF/upf{i}cfg.yaml"
        with open(path, "w") as f:
            yaml.dump(upf_config, f, default_flow_style=False, sort_keys=False)
        upf_config_paths.append(path)
    
    # Generate SMF configuration
    smf_config_path = "config/multiUPF/smf-multi-cfg.yaml"
    smf_config = generate_smf_config(num_upfs)
    with open(smf_config_path, "w") as f:
        yaml.dump(smf_config, f, default_flow_style=False, sort_keys=False)
    
    # Generate UE routing configuration
    uerouting_config_path = "config/multiUPF/uerouting-multi.yaml"
    uerouting_config = generate_uerouting_config(num_upfs)
    with open(uerouting_config_path, "w") as f:
        yaml.dump(uerouting_config, f, default_flow_style=False, sort_keys=False)
    
    return {
        "docker_compose": docker_compose_path,
        "upf_configs": upf_config_paths,
        "smf_config": smf_config_path,
        "uerouting_config": uerouting_config_path
    }

if __name__ == "__main__":
    # This is kept for backward compatibility, but the main usage should be through the new file
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <number_of_upfs>")
        sys.exit(1)
    
    try:
        num_upfs = int(sys.argv[1])
        result = create_upf_topology(num_upfs)
        
        print(f"Generated Docker Compose configuration with {num_upfs} UPFs: {result['docker_compose']}")
        for i, path in enumerate(result['upf_configs'], 1):
            print(f"Generated UPF{i} configuration: {path}")
        print(f"Generated SMF configuration: {result['smf_config']}")
        print(f"Generated UE routing configuration: {result['uerouting_config']}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)






