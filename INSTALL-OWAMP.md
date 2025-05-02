OWAMP Network Metrics Tool - Installation Guide
This guide provides instructions for installing OWAMP (One-Way Active Measurement Protocol) on Docker containers for network performance testing.

Prerequisites
Docker installed and running
Two containers (source and destination) where you want to run the tests
Root or sudo access to the containers

Installation Steps (Run the commands on both source and detination containers)
1. Install Required Dependencies
# Update packages and install build dependencies
apt update
apt install -y build-essential autoconf automake libtool pkg-config git groff


2. Install i2util Library
i2util is a required dependency for OWAMP:
# Download i2util
git clone https://github.com/perfsonar/i2util.git
cd i2util

# Find and navigate to directory containing bootstrap
cd $(find . -type f -name bootstrap -exec dirname {} \; | head -n 1)

# Build and install
./bootstrap
./configure
make
make install
ldconfig  # Update shared library cache


3. Install OWAMP
After installing i2util, install OWAMP:
# Return to your main directory (where you installed i2util)
cd /path/to/your/main/directory  # Replace with your actual path

# Download OWAMP
git clone https://github.com/perfsonar/owamp.git
cd owamp

# Find and navigate to directory containing bootstrap
cd $(find . -type f -name bootstrap -exec dirname {} \; | head -n 1)

# Build and install
./bootstrap
./configure
make
make install
ldconfig