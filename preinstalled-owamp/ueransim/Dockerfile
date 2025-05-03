FROM gcc:9.4.0 AS builder
LABEL maintainer="Free5GC <support@free5gc.org>"
ENV DEBIAN_FRONTEND=noninteractive
# Install dependencies
RUN apt-get update \
    && apt-get install libsctp-dev lksctp-tools iproute2 -y \
    && wget https://github.com/Kitware/CMake/releases/download/v3.22.1/cmake-3.22.1-linux-x86_64.sh -O cmake_installer.sh \
    && chmod +x cmake_installer.sh \
    && ./cmake_installer.sh --skip-license \
    && git clone -b master -j `nproc` https://github.com/aligungr/UERANSIM \
    && cd ./UERANSIM \
    && make

FROM bitnami/minideb:bullseye
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies + ping
RUN apt-get update \
    && apt-get install libsctp-dev lksctp-tools iproute2 iputils-ping procps psmisc -y \
    # Install build dependencies for OWAMP
    && apt-get install -y build-essential autoconf automake libtool pkg-config git groff \
    && apt-get clean

# Install i2util (dependency for OWAMP)
WORKDIR /tmp
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

WORKDIR /ueransim
RUN mkdir -p config/ binder/
COPY --from=builder /UERANSIM/build/nr-gnb .
COPY --from=builder /UERANSIM/build/nr-ue .
COPY --from=builder /UERANSIM/build/nr-cli .
COPY --from=builder /UERANSIM/build/nr-binder binder/
COPY --from=builder /UERANSIM/build/libdevbnd.so binder/

# Add volumes for both UERANSIM config and OWAMP data
VOLUME ["/ueransim/config", "/var/lib/owamp"]
