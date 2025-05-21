def generate_upf_config(hostname, is_edge=False, is_psa=False, is_server=False):
    """Generate UPF configuration file for a specific UPF node"""
    
    config = {
        "version": "1.0.3",
        "description": f"UPF initial local configuration for {hostname}",
        "pfcp": {
            "addr": f"{hostname}.free5gc.org",
            "nodeID": f"{hostname}.free5gc.org",
            "retransTimeout": "1s",
            "maxRetrans": 3
        },
        "gtpu": {
            "forwarder": "gtp5g",
            "ifList": []
        },
        "dnnList": [
            {
                "dnn": "remote-surgery",
                "cidr": "10.60.0.0/16"
            }
        ],
        "logger": {
            "enable": True,
            "level": "info",
            "reportCaller": False
        }
    }
    
    # Add interfaces based on UPF type
    if is_edge:
        config["gtpu"]["ifList"].append(
            {
                "addr": f"{hostname}.free5gc.org",
                "type": "N3"
            }
        )
    
    if not is_psa or (is_psa and not is_edge):
        # All intermediate UPFs and PSA UPF need N9 interfaces
        config["gtpu"]["ifList"].append(
            {
                "addr": f"{hostname}.free5gc.org",
                "type": "N9"
            }
        )
    
    # Custom server specific configuration
    if is_server:
        config["dnnList"][0]["cidr"] = "10.70.0.0/16"  # Different IP range for server
    
    return config


def generate_docker_compose(num_upfs, edge_upfs, is_server=False):
    """Generate docker-compose configuration for the specified number of UPFs"""
    
    services = {}
    
    # Generate intermediate UPF services
    for i in range(1, num_upfs):
        hostname = f"i-upf{i}" if i > 1 else "i-upf"
        
        services[f"free5gc-{hostname}"] = {
            "container_name": hostname,
            "image": "free5gc/upf:v4.0.1",
            "command": "bash -c \"./upf-iptables.sh && ./upf -c ./config/upfcfg.yaml\"",
            "volumes": [
                f"./config/custom/upfcfg-{hostname}.yaml:/free5gc/config/upfcfg.yaml",
                "./config/upf-iptables.sh:/free5gc/upf-iptables.sh"
            ],
            "cap_add": ["NET_ADMIN"],
            "networks": {
                "privnet": {
                    "aliases": [f"{hostname}.free5gc.org"]
                }
            }
        }
    
    # Generate PSA UPF service
    services["free5gc-remote-surgery"] = {
        "container_name": "remote-surgery",
        "image": "ikramdh18/custom-upf-owamp:latest",
        "command": "bash -c \"./upf-iptables.sh && ./upf -c ./config/upfcfg.yaml\"",
        "volumes": [
            "./config/custom/upfcfg-psa-upf.yaml:/free5gc/config/upfcfg.yaml",
            "./config/upf-iptables.sh:/free5gc/upf-iptables.sh",
            "./owamp_data:/var/lib/owamp"
        ],
        "cap_add": ["NET_ADMIN"],
        "networks": {
            "privnet": {
                "aliases": ["remote-surgery.free5gc.org"]
            }
        }
    }

    # Generate custom server UPF if enabled
    if is_server:
        services["free5gc-custom-server"] = {
            "container_name": "custom-server",
            "image": "free5gc/upf:v4.0.1",
            "command": "bash -c \"./upf-iptables.sh && ./upf -c ./config/upfcfg.yaml\"",
            "volumes": [
                "./config/custom/upfcfg-custom-server.yaml:/free5gc/config/upfcfg.yaml",
                "./config/upf-iptables.sh:/free5gc/upf-iptables.sh"
            ],
            "cap_add": ["NET_ADMIN"],
            "networks": {
                "privnet": {
                    "aliases": ["custom-server.free5gc.org"]
                }
            }
        }
    
    # Add other existing standard services (reuse from the provided configuration)
    standard_services = {
        "db": {
            "container_name": "mongodb",
            "image": "mongo:3.6.8",
            "command": "mongod --port 27017 --quiet",
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
            "image": "free5gc/nrf:v4.0.1",
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
            "image": "free5gc/amf:v4.0.1",
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
                    "aliases": ["amf.free5gc.org"]
                }
            },
            "depends_on": ["free5gc-nrf"]
        },
        "free5gc-ausf": {
            "container_name": "ausf",
            "image": "free5gc/ausf:v4.0.1",
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
            "image": "free5gc/nssf:v4.0.1",
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
            "image": "free5gc/pcf:v4.0.1",
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
    }
    
    services.update(standard_services)
    
    # Add SMF service with dependencies on all UPFs
    upf_dependencies = ["free5gc-nrf"]
    for i in range(1, num_upfs):
        hostname = f"i-upf{i}" if i > 1 else "i-upf"
        upf_dependencies.append(f"free5gc-{hostname}")
    upf_dependencies.append("free5gc-remote-surgery")
    
    if is_server:
        upf_dependencies.append("free5gc-custom-server")
    
    services["free5gc-smf"] = {
        "container_name": "smf",
        "image": "free5gc/smf:v4.0.1",
        "command": "./smf -c ./config/smfcfg.yaml -u ./config/uerouting.yaml",
        "expose": ["8000"],
        "volumes": [
            "./config/custom/smfcfg.yaml:/free5gc/config/smfcfg.yaml",
            "./config/custom/uerouting.yaml:/free5gc/config/uerouting.yaml",
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
        "depends_on": upf_dependencies
    }
    
    # Add remaining standard services
    remaining_services = {
        "free5gc-udm": {
            "container_name": "udm",
            "image": "free5gc/udm:v4.0.1",
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
            "image": "free5gc/udr:v4.0.1",
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
        "free5gc-chf": {
            "container_name": "chf",
            "image": "free5gc/chf:v4.0.1",
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
        },
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
        },
        "free5gc-webui": {
            "container_name": "webui",
            "image": "free5gc/webui:v4.0.1",
            "command": "./webui -c ./config/webuicfg.yaml",
            "expose": ["2122", "2121"],
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
            "ports": [
                "5000:5000",
                "2122:2122",
                "2121:2121"
            ],
            "depends_on": ["db", "free5gc-nrf"]
        }
    }
    
    services.update(remaining_services)
    
    # Add UERANSIM with dependencies on UPFs
    ueransim_dependencies = ["free5gc-amf"]
    for i in range(1, num_upfs):
        hostname = f"i-upf{i}" if i > 1 else "i-upf"
        ueransim_dependencies.append(f"free5gc-{hostname}")
    ueransim_dependencies.append("free5gc-remote-surgery")
    
    if is_server:
        ueransim_dependencies.append("free5gc-custom-server")
    
    services["ueransim"] = {
        "container_name": "ueransim",
        "image": "ikramdh18/custom-ueransim-owamp:latest",
        "command": "./nr-gnb -c ./config/gnbcfg.yaml",
        "volumes": [
            "./config/gnbcfg.yaml:/ueransim/config/gnbcfg.yaml",
            "./config/uecfg-custom.yaml:/ueransim/config/uecfg.yaml",
            "./owamp_data:/var/lib/owamp"
        ],
        "cap_add": ["NET_ADMIN"],
        "devices": ["/dev/net/tun"],
        "networks": {
            "privnet": {
                "aliases": ["gnb.free5gc.org"]
            }
        },
        "depends_on": ueransim_dependencies
    }
    
    # Full docker-compose config
    compose = {
        "version": "3.8",
        "services": services,
        "networks": {
            "privnet": {
                "ipam": {
                    "driver": "default",
                    "config": [
                        {"subnet": "10.100.200.0/24"}
                    ]
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
    
    return compose


def generate_smf_config(num_upfs, edge_upfs, is_server=False):
    """Generate SMF configuration with proper UPF topology"""
    
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
                            "dnn": "remote-surgery",
                            "dnaiList": ["mec"],
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
                "upNodes": {},
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
            "requestedUnit": 1000,
            "ulcl": True,
            "ueRouting": {
                "enable": True,
                "path": "./uerouting.yaml"
            }
        },
        "logger": {
            "enable": True,
            "level": "info",
            "reportCaller": False
        }
    }
    
    # Add gNB node
    smf_config["configuration"]["userplaneInformation"]["upNodes"]["gNB1"] = {
        "type": "AN",
        "nodeID": "gnb.free5gc.org"
    }
    
    # Add intermediate UPF nodes
    for i in range(1, num_upfs):
        hostname = f"i-upf{i}" if i > 1 else "i-upf"
        is_edge = i <= edge_upfs
        
        upf_node = {
            "type": "UPF",
            "nodeID": f"{hostname}.free5gc.org",
            "sNssaiUpfInfos": [
                {
                    "sNssai": {
                        "sst": 1,
                        "sd": "010203"
                    },
                    "dnnUpfInfoList": [
                        {
                            "dnn": "remote-surgery",
                            "dnaiList": ["mec"]
                        }
                    ]
                }
            ],
            "interfaces": []
        }
        
        # Add N3 interface if edge UPF
        if is_edge:
            upf_node["interfaces"].append({
                "interfaceType": "N3",
                "endpoints": [f"{hostname}.free5gc.org"],
                "networkInstances": ["remote-surgery"]
            })
        
        # Add N9 interface for all intermediate UPFs
        upf_node["interfaces"].append({
            "interfaceType": "N9",
            "endpoints": [f"{hostname}.free5gc.org"],
            "networkInstances": ["remote-surgery"]
        })
        
        smf_config["configuration"]["userplaneInformation"]["upNodes"][hostname.upper()] = upf_node
    
    # Add PSA UPF node
    smf_config["configuration"]["userplaneInformation"]["upNodes"]["REMOTE-SURGERY"] = {
        "type": "UPF",
        "nodeID": "remote-surgery.free5gc.org",
        "sNssaiUpfInfos": [
            {
                "sNssai": {
                    "sst": 1,
                    "sd": "010203"
                },
                "dnnUpfInfoList": [
                    {
                        "dnn": "remote-surgery",
                        "pools": [
                            {
                                "cidr": "10.60.0.0/16"
                            }
                        ]
                    }
                ]
            }
        ],
        "interfaces": [
            {
                "interfaceType": "N9",
                "endpoints": ["remote-surgery.free5gc.org"],
                "networkInstances": ["remote-surgery"]
            }
        ]
    }
    
    # Add custom server UPF if enabled
    if is_server:
        smf_config["configuration"]["userplaneInformation"]["upNodes"]["CUSTOM-SERVER"] = {
            "type": "UPF",
            "nodeID": "custom-server.free5gc.org",
            "sNssaiUpfInfos": [
                {
                    "sNssai": {
                        "sst": 1,
                        "sd": "010203"
                    },
                    "dnnUpfInfoList": [
                        {
                            "dnn": "remote-surgery",
                            "pools": [
                                {
                                    "cidr": "10.70.0.0/16"
                                }
                            ]
                        }
                    ]
                }
            ],
            "interfaces": [
                {
                    "interfaceType": "N9",
                    "endpoints": ["custom-server.free5gc.org"],
                    "networkInstances": ["remote-surgery"]
                }
            ]
        }
    
    # Generate linear links between nodes
    links = []

    # First link: gNB1 to first UPF
    first_upf = "i-upf"
    links.append({
        "A": "gNB1",
        "B": first_upf.upper()
    })

    # Intermediate UPFs chain
    for i in range(1, num_upfs - 1):
        upf_a = f"i-upf{i}" if i > 1 else "i-upf"
        upf_b = f"i-upf{i+1}"
        links.append({
            "A": upf_a.upper(),
            "B": upf_b.upper()
        })

    # Final link: last intermediate UPF to PSA-UPF
    last_upf = f"i-upf{num_upfs - 1}" if num_upfs > 2 else "i-upf"
    links.append({
        "A": last_upf.upper(),
        "B": "REMOTE-SURGERY"
    })
    
    # Add link from PSA-UPF to custom server if enabled
    if is_server:
        links.append({
            "A": "REMOTE-SURGERY",
            "B": "CUSTOM-SERVER"
        })
    
    # Add links to SMF config
    smf_config["configuration"]["userplaneInformation"]["links"] = links
    
    return smf_config


def generate_uerouting_config(num_upfs, edge_upfs, is_server=False):
    """Generate UE routing configuration with default path through all UPFs"""
    
    # Create the default path through all UPFs
    topology = []
    
    # First link: gNB1 -> first edge UPF
    first_upf = "I-UPF"  # Default to first UPF
    topology.append({
        "A": "gNB1",
        "B": first_upf
    })
    
    # Connect all intermediate UPFs in sequence
    for i in range(1, num_upfs - 1):
        source = f"I-UPF{i}" if i > 1 else "I-UPF"
        target = f"I-UPF{i+1}" if i+1 > 1 else "I-UPF"
        topology.append({
            "A": source,
            "B": target
        })
    
    # Final link to PSA-UPF
    last_i_upf = f"I-UPF{num_upfs-1}" if num_upfs > 2 else "I-UPF"
    topology.append({
        "A": last_i_upf,
        "B": "REMOTE-SURGERY"
    })
    
    # Add link to custom server if enabled
    if is_server:
        topology.append({
            "A": "REMOTE-SURGERY",
            "B": "CUSTOM-SERVER"
        })
    
    # Create a default path for specific traffic
    path = []
    for i in range(1, num_upfs):
        upf_name = f"I-UPF{i}" if i > 1 else "I-UPF"
        path.append(upf_name)
    path.append("REMOTE-SURGERY")
    
    if is_server:
        path.append("CUSTOM-SERVER")
    
    ue_routing = {
        "info": {
            "version": "1.0.7",
            "description": "Routing information for UE"
        },
        "ueRoutingInfo": {
            "UE1": {
                "members": [
                    "imsi-208930000000001"
                ],
                "topology": topology,
                "specificPath": [
                    {
                        "dest": "1.0.0.1/32",
                        "path": path
                    }
                ]
            }
        },
        "pfdDataForApp": [
            {
                "applicationId": "app1",
                "pfds": [
                    {
                        "pfdID": "pfd1",
                        "flowDescriptions": [
                            "permit out ip from 1.0.0.1/32 to 10.60.0.0/16"
                        ]
                    }
                ]
            }
        ]
    }
    
    return ue_routing

