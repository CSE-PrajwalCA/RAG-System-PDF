FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PGDATA=/data/shaktidb_utf8
ENV PATH="/usr/lib/postgresql/17.4.0.4/bin:$PATH"
# UTF-8 MUST be set at build time and propagated to runtime
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

VOLUME /data

# Install locale support BEFORE anything else that depends on locales
RUN apt-get update && apt-get install -y \
    locales \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Verify locale was generated correctly (CRITICAL diagnostic)
RUN locale -a | grep -i "en_US" || (echo "FATAL: en_US.UTF-8 locale not found" && exit 1)

# Runtime dependencies REQUIRED by ShaktiDB/PostgreSQL binary
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    tzdata \
    libssl3 \
    libkrb5-3 \
    libgssapi-krb5-2 \
    libldap2 \
    libcurl4 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy ShaktiDB installer
COPY shaktidb_17.4.0.4_ubuntu24.04_amd64.deb /tmp/shaktidb.deb

# Install ShaktiDB
RUN apt-get update && apt-get install -y /tmp/shaktidb.deb \
    && apt-get clean && rm -f /tmp/shaktidb.deb && rm -rf /var/lib/apt/lists/*

# Ensure postgres user exists
RUN id postgres || useradd -m postgres

# SSL setup (as per ShaktiDB handbook)
RUN mkdir -p /etc/ssl/shaktidb/server && \
    openssl req -new -x509 -days 365 -nodes \
    -out /etc/ssl/shaktidb/server/server.crt \
    -keyout /etc/ssl/shaktidb/server/server.key \
    -subj "/CN=shaktidb" && \
    chown -R postgres:postgres /etc/ssl/shaktidb && \
    chmod 600 /etc/ssl/shaktidb/server/server.key && \
    chmod 644 /etc/ssl/shaktidb/server/server.crt

# Data directory with proper permissions
RUN mkdir -p /data/shaktidb_utf8 && chown -R postgres:postgres /data && chmod 700 /data/shaktidb_utf8

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install build dependencies and compile pgvector from source
# We need to add PGDG repo to get postgresql-server-dev-17 on Ubuntu 24.04
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    lsb-release \
    curl \
    gnupg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y postgresql-server-dev-17 \
    && git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make clean \
    && make PG_CONFIG=/usr/lib/postgresql/17/bin/pg_config \
    && make install PG_CONFIG=/usr/lib/postgresql/17/bin/pg_config \
    && cd / \
    && rm -rf /tmp/pgvector \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 15234

# DO NOT set USER postgres here - entrypoint needs to run as root first
ENTRYPOINT ["/entrypoint.sh"]
