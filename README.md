# UPF Placement and URLLC Traffic Simulation
This project provides a framework for simulating UPF (User Plane Function) placement based on geographic coordinates and testing network performance through ping measurements.

## Project Structure
```
├── main.py                  # Main entry point with combined functionality
├── utils/
│   ├── apply_distance.py    # Contains functions for coordinate-based bandwidth limitation
│   └── ping_and_measure.py  # Contains functions for UE authentication and ping testing
└── configurations/
    └── uecfg*.yaml          # UE  and other container configuration files
```

## Features
- Configure network bandwidth limitations based on geographic distances between components
- Authenticate UEs (User Equipment) and perform ping measurements
- Save test results for analysis

## Getting Started
### Requirements
- Python 3.8 or later
- `pip` (Python package manager)
- Docker
- Docker SDK for Python (`pip install docker`)
- free5gc docker compose on Ubuntu VM ([check this](https://lobna.me/setting-up-the-environment-for-free5gc))

### Setup
1. Clone the repository:
    ```bash
    git clone https://github.com/minaiscoding/upf-placement-simulator
    cd upf-placement-simulator
    ```
2. (Optional) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    ```
3. Install dependencies:
    ```bash
    pip install docker
    ```
4. Run the simulation:
    ```bash
    python main.py
    ```

### Command Line Options
The main script supports various command line arguments:

```
usage: main.py [-h] [--skip-distance] [-n NUM_UES] [-s PACKET_SIZE] [-c CONFIG_PREFIX] [-r] [-p PING_COUNT] [-i INTERVAL] [-q QOS] [--skip-ping]

Free5GC Network Testing Tool with Distance Simulation

optional arguments:
  -h, --help            show this help message and exit
  --skip-distance       Skip distance configuration
  -n NUM_UES, --num_ues NUM_UES
                        Number of UEs to authenticate
  -s PACKET_SIZE, --packet_size PACKET_SIZE
                        Ping packet size in bytes
  -c CONFIG_PREFIX, --config_prefix CONFIG_PREFIX
                        Prefix for UE config files
  -r, --restart         Restart all UE processes
  -p PING_COUNT, --ping_count PING_COUNT
                        Number of ping packets per interface
  -i INTERVAL, --interval INTERVAL
                        Interval between pings in seconds
  -q QOS, --qos QOS     QoS value in hex format
  --skip-ping           Skip ping measurements
```

---
## Contributing
To contribute new features or modify existing ones, follow the Git workflow below.

### Git Workflow
1. **Pull the latest changes:**
    ```bash
    git checkout main
    git pull origin main
    ```
2. **Create a new feature branch:**
    ```bash
    git checkout -b feature/<short-description>
    ```
3. **Implement your feature.**  
   Example locations for adding functionality:
   - Add new UPF logic in `utils/apply_distance.py`
   - Extend or improve ping measurements in `utils/ping_and_measure.py`
   - Modify orchestration flow in `main.py`
4. **Stage and commit your changes:**
    ```bash
    git add .
    git commit -m "Add <brief-description-of-change>"
    ```
5. **Push your feature branch:**
    ```bash
    git push origin feature/<short-description>
    ```
6. **Open a Pull Request (PR)** on GitHub and tag reviewers.

---
## Adding New Functionality
All logic should be modular and located under the `utils/` directory. Each file should contain clearly named functions that can be imported into `main.py`.

### Example
To add a new analytics module:
1. Create a new file: `utils/analytics.py`
2. Define your function:
    ```python
    def evaluate_performance():
        # Implementation goes here
        pass
    ```
3. Import and call it from `main.py` as needed.

---
## Output
Upon successful execution, the program will:
1. Prompt for geographic coordinates
2. Calculate and apply bandwidth limitations based on distances
3. Authenticate the specified number of UEs
4. Perform ping measurements
5. Save results to `ping_result.txt`

Example output:
```
=== Free5GC Network Testing Tool ===

=== Configuration des limitations de bande passante basées sur la distance ===

UE-RANSIM coordinates (from docker-compose-ulcl.yaml):
  Latitude: 45.7640
  Longitude: 4.8357

Veuillez entrer les coordonnées pour i-upf:
  Latitude: 45.7641
  Longitude: 4.8358

Veuillez entrer les coordonnées pour psa-upf:
  Latitude: 45.7642
  Longitude: 4.8359

Résultats calculés:
Distance ueransim → i-upf: 0.17 km
Bande passante estimée: 998.35 Mbps
Distance i-upf → psa-upf: 0.17 km
Bande passante estimée: 998.35 Mbps

Configuration des distances terminée avec succès.

=== Exécution des tests de ping ===

[INFO] Found UPF container 'psa-upf' with IP: 10.60.0.103
[INFO] Starting authentication for UE 1 using config/uecfg1.yaml
[INFO] Waiting for interface uesimtun0 to be created...
[SUCCESS] UE 1 authenticated successfully, interfaces created: uesimtun0

[INFO] Found 1 data interfaces: uesimtun0
[INFO] Waiting 3 seconds for network stability...
[INFO] Pinging 10.60.0.103 from interface uesimtun0 with packet size 8...
[✓] Interface uesimtun0: RTT=0.384ms, Loss=0%

[INFO] Results saved to ping_result.txt
[INFO] Cleaning up UE interfaces...

=== Traitement terminé ===
```
