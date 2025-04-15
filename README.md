# UPF Placement and URLLC Traffic Simulation

This project provides a basic framework for simulating UPF (User Plane Function) placement and generating URLLC (Ultra-Reliable Low Latency Communications) traffic.

## Project Structure

├── main.py
└── utils
 ├── distance.py # Contains configure_upf_placement 
 └── traffic.py # Contains generate_urllc_traffic


## Getting Started

### Requirements

- Python 3.8 or later
- `pip` (Python package manager)
- free5g docker compose on ubuntu vm ([check this](https://lobna.me/setting-up-the-environment-for-free5gc))

### Setup

1. Clone the repository:
    ```bash
    git clone <your-repo-url>
    cd <repo-name>
    ```

2. (Optional) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate   # Windows
    ```

3. Install dependencies (if any are added later):
    ```bash
    pip install -r requirements.txt
    ```

4. Run the simulation:
    ```bash
    python main.py
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
   - Add new UPF logic in `utils/distance.py`
   - Extend or simulate traffic behavior in `utils/traffic.py`
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

Upon successful execution, the program will print:

