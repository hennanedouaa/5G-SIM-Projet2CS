# Start from the base UPF image
FROM free5gc/upf:latest

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    groff \
    && rm -rf /var/lib/apt/lists/*

# Install i2util (dependency for OWAMP)
WORKDIR /free5gc
RUN git clone https://github.com/perfsonar/i2util.git && \
    cd i2util && \
    cd $(find . -type f -name bootstrap -exec dirname {} \; | head -n 1) && \
    ./bootstrap && \
    ./configure && \
    make && \
    make install && \
    ldconfig

# Install OWAMP
RUN git clone https://github.com/perfsonar/owamp.git && \
    cd owamp && \
    cd $(find . -type f -name bootstrap -exec dirname {} \; | head -n 1) && \
    ./bootstrap && \
    ./configure && \
    make && \
    make install && \
    ldconfig

# Create OWAMP directories
RUN mkdir -p /etc/owamp /var/lib/owamp

# Cleanup
RUN rm -rf /tmp/i2util /tmp/owamp
