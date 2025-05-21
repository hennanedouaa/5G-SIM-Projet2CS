import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def login(username, password):
    url = f"{BASE_URL}/api/login"
    resp = requests.post(url, json={"username": username, "password": password})
    if resp.status_code == 200:
        data = resp.json()
        token = data.get("access_token")
        if not token:
            print("Login succeeded but no token found:", data)
            return None
        return token
    else:
        print(f"Login failed: {resp.status_code}, {resp.text}")
        return None

BASE_URL = "http://127.0.0.1:5000"

def insert_ue(number):
    ue_id = f"imsi-20893000000000{number}"
    plmn = "20893"
    url = f"{BASE_URL}/api/subscriber/{ue_id}/{plmn}"
    
    # Fixed token from the curl command
    token = login("admin","free5gc")

    payload = {
        "userNumber": 1,
        "ueId": ue_id,
        "plmnID": plmn,
        "AuthenticationSubscription": {
            "authenticationMethod": "5G_AKA",
            "permanentKey": {
                "permanentKeyValue": "8baf473f2f8fd09487cccbd7097c6862",
                "encryptionKey": 0,
                "encryptionAlgorithm": 0
            },
            "sequenceNumber": "000000000023",
            "authenticationManagementField": "8000",
            "milenage": {
                "op": {
                    "opValue": "",
                    "encryptionKey": 0,
                    "encryptionAlgorithm": 0
                }
            },
            "opc": {
                "opcValue": "8e27b6af0e692e750f32667a3b14605d",
                "encryptionKey": 0,
                "encryptionAlgorithm": 0
            }
        },
        "AccessAndMobilitySubscriptionData": {
            "gpsis": ["msisdn-"],
            "subscribedUeAmbr": {
                "uplink": "1 Gbps",
                "downlink": "2 Gbps"
            },
            "nssai": {
                "defaultSingleNssais": [{"sst": 1, "sd": "010203"}],
                "singleNssais": [{"sst": 1, "sd": "112233"}]
            }
        },
        "SessionManagementSubscriptionData": [
            {
                "singleNssai": {"sst": 1, "sd": "010203"},
                "dnnConfigurations": {
                    "internet": {
                        "pduSessionTypes": {
                            "defaultSessionType": "IPV4",
                            "allowedSessionTypes": ["IPV4"]
                        },
                        "sscModes": {
                            "defaultSscMode": "SSC_MODE_1",
                            "allowedSscModes": ["SSC_MODE_2", "SSC_MODE_3"]
                        },
                        "5gQosProfile": {
                            "5qi": 9,
                            "arp": {
                                "priorityLevel": 8,
                                "preemptCap": "",
                                "preemptVuln": ""
                            },
                            "priorityLevel": 8
                        },
                        "sessionAmbr": {
                            "uplink": "1000 Mbps",
                            "downlink": "1000 Mbps"
                        },
                        "staticIpAddress": []
                    }
                }
            },
            {
                "singleNssai": {"sst": 1, "sd": "112233"},
                "dnnConfigurations": {
                    "internet": {
                        "pduSessionTypes": {
                            "defaultSessionType": "IPV4",
                            "allowedSessionTypes": ["IPV4"]
                        },
                        "sscModes": {
                            "defaultSscMode": "SSC_MODE_1",
                            "allowedSscModes": ["SSC_MODE_2", "SSC_MODE_3"]
                        },
                        "5gQosProfile": {
                            "5qi": 8,
                            "arp": {
                                "priorityLevel": 8,
                                "preemptCap": "",
                                "preemptVuln": ""
                            },
                            "priorityLevel": 8
                        },
                        "sessionAmbr": {
                            "uplink": "1000 Mbps",
                            "downlink": "1000 Mbps"
                        },
                        "staticIpAddress": []
                    }
                }
            }
        ],
        "SmfSelectionSubscriptionData": {
            "subscribedSnssaiInfos": {
                "01010203": {
                    "dnnInfos": [{"dnn": "internet"}]
                },
                "01112233": {
                    "dnnInfos": [{"dnn": "internet"}]
                }
            }
        },
        "AmPolicyData": {
            "subscCats": ["free5gc"]
        },
        "SmPolicyData": {
            "smPolicySnssaiData": {
                "01010203": {
                    "snssai": {"sst": 1, "sd": "010203"},
                    "smPolicyDnnData": {
                        "internet": {"dnn": "internet"}
                    }
                },
                "01112233": {
                    "snssai": {"sst": 1, "sd": "112233"},
                    "smPolicyDnnData": {
                        "internet": {"dnn": "internet"}
                    }
                }
            }
        },
        "FlowRules": [
            {
                "filter": "1.1.1.1/32",
                "precedence": 128,
                "snssai": "01010203",
                "dnn": "internet",
                "qosRef": 1
            },
            {
                "filter": "1.1.1.1/32",
                "precedence": 127,
                "snssai": "01112233",
                "dnn": "internet",
                "qosRef": 2
            }
        ],
        "QosFlows": [
            {
                "snssai": "01010203",
                "dnn": "internet",
                "qosRef": 1,
                "5qi": 8,
                "mbrUL": "208 Mbps",
                "mbrDL": "208 Mbps",
                "gbrUL": "108 Mbps",
                "gbrDL": "108 Mbps"
            },
            {
                "snssai": "01112233",
                "dnn": "internet",
                "qosRef": 2,
                "5qi": 7,
                "mbrUL": "407 Mbps",
                "mbrDL": "407 Mbps",
                "gbrUL": "207 Mbps",
                "gbrDL": "207 Mbps"
            }
        ],
        "ChargingDatas": [
            {
                "chargingMethod": "Offline",
                "quota": "100000",
                "unitCost": "1",
                "snssai": "01010203",
                "dnn": "",
                "filter": ""
            },
            {
                "chargingMethod": "Offline",
                "quota": "100000",
                "unitCost": "1",
                "snssai": "01010203",
                "dnn": "internet",
                "filter": "1.1.1.1/32",
                "qosRef": 1
            },
            {
                "chargingMethod": "Online",
                "quota": "100000",
                "unitCost": "1",
                "snssai": "01112233",
                "dnn": "",
                "filter": ""
            },
            {
                "chargingMethod": "Online",
                "quota": "5000",
                "unitCost": "1",
                "snssai": "01112233",
                "dnn": "internet",
                "filter": "1.1.1.1/32",
                "qosRef": 2
            }
        ]
    }

    headers = {
        "Token": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "http://127.0.0.1:5000",
        "Connection": "keep-alive",
        "Referer": "http://127.0.0.1:5000/subscriber/create",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(f"Inserted UE {ue_id}: Status Code {response.status_code}")
    if response.status_code != 200:
        print("Response:", response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <X>")
        print("Where X is the last digit of the IMSI (imsi-20893000000000X)")
        sys.exit(1)
        
    number = sys.argv[1]
    insert_ue(number)

