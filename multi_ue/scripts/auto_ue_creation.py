#!/usr/bin/env python3

import os
import yaml
import argparse
import subprocess
from datetime import datetime

def generate_mongo_commands(ue_id, tenant_id):
    """Génère les commandes MongoDB pour un UE donné"""
    commands = []

    # 1. Authentication Subscription
    commands.append(f"""
db.getCollection("subscriptionData.authenticationData.authenticationSubscription").insertOne({{
  "ueId": "{ue_id}",
  "tenantId": "{tenant_id}",
  "authenticationMethod": "5G_AKA",
  "permanentKey": {{
    "encryptionAlgorithm": 0,
    "encryptionKey": 0,
    "permanentKeyValue": "8baf473f2f8fd09487cccbd7097c6862"
  }},
  "sequenceNumber": "00000000006f",
  "authenticationManagementField": "8000",
  "milenage": {{
    "op": {{
      "encryptionAlgorithm": 0,
      "encryptionKey": 0,
      "opValue": ""
    }}
  }},
  "opc": {{
    "encryptionAlgorithm": 0,
    "encryptionKey": 0,
    "opcValue": "8e27b6af0e692e750f32667a3b14605d"
  }}
}})
""")

    # 2. Authentication Status
    commands.append(f"""
db.getCollection("subscriptionData.authenticationData.authenticationStatus").insertOne({{
  "nfInstanceId": "029d6a90-3382-481f-acc1-71d9d5112aa7",
  "success": true,
  "timeStamp": "{datetime.now().isoformat()}",
  "authType": "5G_AKA",
  "servingNetworkName": "5G:mnc093.mcc208.3gppnetwork.org",
  "ueId": "{ue_id}"
}})
""")

    # 3. AM Data
    commands.append(f"""
db.getCollection("subscriptionData.provisionedData.amData").insertOne({{
  "ueId": "{ue_id}",
  "servingPlmnId": "20893",
  "tenantId": "{tenant_id}",
  "gpsis": ["msisdn-"],
  "subscribedUeAmbr": {{
    "uplink": "1 Gbps",
    "downlink": "2 Gbps"
  }},
  "nssai": {{
    "defaultSingleNssais": [
      {{
        "sst": 1,
        "sd": "010203"
      }}
    ],
    "singleNssais": [
      {{
        "sst": 1,
        "sd": "112233"
      }}
    ]
  }}
}})
""")

    # 4. SM Data for first slice (010203)
    commands.append(f"""
db.getCollection("subscriptionData.provisionedData.smData").insertOne({{
  "ueId": "{ue_id}",
  "servingPlmnId": "20893",
  "singleNssai": {{
    "sst": 1,
    "sd": "010203"
  }},
  "dnnConfigurations": {{
    "internet": {{
      "pduSessionTypes": {{
        "defaultSessionType": "IPV4",
        "allowedSessionTypes": ["IPV4"]
      }},
      "sscModes": {{
        "defaultSscMode": "SSC_MODE_1",
        "allowedSscModes": ["SSC_MODE_2", "SSC_MODE_3"]
      }},
      "5gQosProfile": {{
        "5qi": 9,
        "arp": {{
          "priorityLevel": 8,
          "preemptCap": "",
          "preemptVuln": ""
        }},
        "priorityLevel": 8
      }},
      "sessionAmbr": {{
        "uplink": "1000 Mbps",
        "downlink": "1000 Mbps"
      }}
    }}
  }}
}})
""")

    # 5. SM Data for second slice (112233)
    commands.append(f"""
db.getCollection("subscriptionData.provisionedData.smData").insertOne({{
  "ueId": "{ue_id}",
  "servingPlmnId": "20893",
  "singleNssai": {{
    "sst": 1,
    "sd": "112233"
  }},
  "dnnConfigurations": {{
    "internet": {{
      "pduSessionTypes": {{
        "defaultSessionType": "IPV4",
        "allowedSessionTypes": ["IPV4"]
      }},
      "sscModes": {{
        "defaultSscMode": "SSC_MODE_1",
        "allowedSscModes": ["SSC_MODE_2", "SSC_MODE_3"]
      }},
      "5gQosProfile": {{
        "5qi": 8,
        "arp": {{
          "priorityLevel": 8,
          "preemptCap": "",
          "preemptVuln": ""
        }},
        "priorityLevel": 8
      }},
      "sessionAmbr": {{
        "uplink": "1000 Mbps",
        "downlink": "1000 Mbps"
      }}
    }}
  }}
}})
""")

    # 6. SMF Selection Subscription Data
    commands.append(f"""
db.getCollection("subscriptionData.provisionedData.smfSelectionSubscriptionData").insertOne({{
  "ueId": "{ue_id}",
  "servingPlmnId": "20893",
  "subscribedSnssaiInfos": {{
    "01010203": {{
      "dnnInfos": [
        {{
          "dnn": "internet"
        }},
        {{
          "dnn": "internet"
        }}
      ]
    }},
    "01112233": {{
      "dnnInfos": [
        {{
          "dnn": "internet"
        }},
        {{
          "dnn": "internet"
        }}
      ]
    }}
  }}
}})
""")

    # 7. Policy AM Data
    commands.append(f"""
db.getCollection("policyData.ues.amData").insertOne({{
  "subscCats": [
    "free5gc"
  ],
  "ueId": "{ue_id}"
}})
""")

    # 8. Policy SM Data
    commands.append(f"""
db.getCollection("policyData.ues.smData").insertOne({{
  "smPolicySnssaiData": {{
    "01010203": {{
      "snssai": {{
        "sst": 1,
        "sd": "010203"
      }},
      "smPolicyDnnData": {{
        "internet": {{
          "dnn": "internet"
        }}
      }}
    }},
    "01112233": {{
      "snssai": {{
        "sst": 1,
        "sd": "112233"
      }},
      "smPolicyDnnData": {{
        "internet": {{
          "dnn": "internet"
        }}
      }}
    }}
  }},
  "ueId": "{ue_id}"
}})
""")

    # 9. Identity Data
    commands.append(f"""
db.getCollection("subscriptionData.identityData").insertOne({{
  "ueId": "{ue_id}",
  "gpsi": "msisdn-"
}})
""")

    return commands

def execute_mongo_commands(commands):
    """Exécute les commandes MongoDB via docker exec"""
    mongo_script = """
use free5gc
""" + "\n".join(commands)

    # Écrire le script dans un fichier temporaire
    with open("temp_mongo_script.js", "w") as f:
        f.write(mongo_script)

    # Exécuter via docker exec
    cmd = ["docker", "exec", "-i", "mongodb", "mongosh", "--quiet"]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
    process.communicate(input=mongo_script)

    # Supprimer le fichier temporaire
    os.remove("temp_mongo_script.js")

def generate_ue_configs(total_ues):
    # Chemins des répertoires
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(scripts_dir, '../config/ue')

    # Vérifier si le répertoire existe
    if not os.path.exists(config_dir):
        print(f"Le répertoire {config_dir} n'existe pas!")
        return

    # Lister les fichiers UE existants
    existing_ues = [f for f in os.listdir(config_dir)
                   if f.startswith('uecfg') and f.endswith('.yaml')]
    existing_count = len(existing_ues)

    # Vérifier si on a déjà assez de fichiers
    if existing_count >= total_ues:
        print(f"Il existe déjà {existing_count} fichiers UE (le total demandé est {total_ues})")
        return

    # Tenant ID (peut être personnalisé)
    tenant_id = "6b8d30f1-c2a4-47e3-989b-72511aef87d8"

    # Charger le modèle de configuration
    template_path = os.path.join(config_dir, 'uecfg1.yaml')
    if not os.path.exists(template_path):
        print(f"Le fichier modèle {template_path} n'existe pas!")
        return

    with open(template_path, 'r') as f:
        template = yaml.safe_load(f)

    # Générer les nouveaux fichiers
    for i in range(existing_count + 1, total_ues + 1):
        # Mettre à jour le SUPI
        new_supi = f"imsi-{template['mcc']}{template['mnc']}{str(i).zfill(10)}"
        template['supi'] = new_supi

        # Générer le nom du fichier
        new_filename = f"uecfg{i}.yaml"
        new_filepath = os.path.join(config_dir, new_filename)

        # Écrire le nouveau fichier
        with open(new_filepath, 'w') as f:
            yaml.dump(template, f, sort_keys=False)

        print(f"Créé {new_filename} avec SUPI: {new_supi}")

        # Générer et exécuter les commandes MongoDB
        mongo_commands = generate_mongo_commands(new_supi, tenant_id)
        execute_mongo_commands(mongo_commands)
        print(f"Données MongoDB insérées pour {new_supi}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Générer des fichiers de configuration UE et les insérer dans MongoDB')
    parser.add_argument('total_ues', type=int,
                       help='Nombre total de fichiers UE souhaités dans le dossier')
    args = parser.parse_args()

    if args.total_ues <= 0:
        print("Le nombre d'UE doit être supérieur à 0.")
        exit(1)

    generate_ue_configs(args.total_ues)
