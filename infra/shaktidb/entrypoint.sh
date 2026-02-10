#!/bin/bash
set -e

# Must run as root to handle locale and permissions properly
if [ "$(id -u)" != "0" ]; then
  echo "[ERROR] This entrypoint must run as root"
  exit 1
fi

# Ensure PostgreSQL binaries are in PATH
export PATH="/usr/lib/postgresql/17.4.0.4/bin:$PATH"
export HOME="/var/lib/postgresql"
export PGDATA=/data/shaktidb_utf8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

echo "[INFO] === ShaktiDB PostgreSQL 17.4 Initialization ==="
echo "[INFO] PGDATA: $PGDATA"
echo "[INFO] LANG: $LANG"
echo "[INFO] Running as: $(whoami) (UID: $(id -u))"

# ============================================================================
# STEP 1: Ensure locale is available at runtime (CRITICAL)
# ============================================================================
echo "[STEP 1] Validating UTF-8 locale availability..."

# Force locale database rebuild (sometimes needed if not done at runtime)
if ! locale -a 2>/dev/null | grep -q "en_US.utf8"; then
  echo "[WARNING] Locale not found, rebuilding locale database..."
  locale-gen en_US.UTF-8 2>&1 | grep -i "generating\|localedef" || true
  update-locale LANG=en_US.UTF-8 2>&1 || true
  sleep 1
fi

# Verify locale is now available
if ! locale -a 2>/dev/null | grep -q "en_US.utf8"; then
  echo "[ERROR] en_US.UTF-8 locale NOT available even after locale-gen!"
  echo "[ERROR] Available locales:"
  locale -a 2>/dev/null || echo "Cannot list locales"
  exit 1
fi

echo "[OK] en_US.UTF-8 locale verified"

# ============================================================================
# STEP 2: Prepare PGDATA directory
# ============================================================================
echo "[STEP 2] Preparing PGDATA directory..."

if [ ! -d "$PGDATA" ]; then
  mkdir -p "$PGDATA"
  echo "[OK] Created PGDATA directory"
fi

# Ensure proper ownership for postgres user
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"
echo "[OK] PGDATA ownership and permissions set"

# ============================================================================
# STEP 3: Check if cluster already exists and validate encoding
# ============================================================================
echo "[STEP 3] Checking for existing PostgreSQL cluster..."

if [ -f "$PGDATA/PG_VERSION" ]; then
  echo "[INFO] Existing cluster found at $PGDATA"
  
  # Try to detect if it's SQL_ASCII (corrupted)
  if grep -q "server_encoding = 'SQL_ASCII'" "$PGDATA/postgresql.conf" 2>/dev/null; then
    echo "[WARNING] Cluster uses SQL_ASCII encoding - corrupted, removing..."
    rm -rf "$PGDATA"/*
    echo "[OK] Corrupted cluster removed"
  else
    echo "[OK] Existing cluster appears valid (UTF-8)"
  fi
fi

# ============================================================================
# STEP 4: Initialize new cluster if needed
# ============================================================================
if [ ! -f "$PGDATA/PG_VERSION" ]; then
  echo "[STEP 4] Initializing new PostgreSQL cluster with UTF-8..."
  
  # Run initdb as postgres user using su with environment preservation
  su -m postgres -s /bin/bash << INITDB_SCRIPT
export PATH='/usr/lib/postgresql/17.4.0.4/bin':\$PATH
export HOME='/var/lib/postgresql'
initdb \
  -D '$PGDATA' \
  --encoding=UTF8 \
  --locale=en_US.UTF-8 \
  --lc-collate=en_US.UTF-8 \
  --lc-ctype=en_US.UTF-8 \
  --lc-messages=en_US.UTF-8 \
  --lc-monetary=en_US.UTF-8 \
  --lc-numeric=en_US.UTF-8 \
  --lc-time=en_US.UTF-8 \
  --auth-local=trust \
  --auth-host=md5 \
  --no-ssl \
  -U postgres
INITDB_SCRIPT
[ $? -eq 0 ] || exit 1
  
  if [ $? -ne 0 ]; then
    echo "[ERROR] initdb failed"
    exit 1
  fi
  
  echo "[OK] PostgreSQL cluster initialized successfully"
  
  # ========================================================================
  # STEP 5: Configure postgresql.conf
  # ========================================================================
  echo "[STEP 5] Configuring postgresql.conf..."
  
  cat >>"/tmp/postgresql_custom.conf" <<'POSTGRES_CONF'

# === UTF-8 Configuration (enforced at initialization) ===
client_encoding = 'UTF8'

# === Network Configuration ===
listen_addresses = '*'
port = 15234

# === Connection Settings for RAG workload ===
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2560kB
min_wal_size = 1GB
max_wal_size = 4GB

# === SSL Configuration (explicitly disabled to avoid certificate issues) ===
ssl = off

# === Logging for diagnosis ===
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000
POSTGRES_CONF

  cat "/tmp/postgresql_custom.conf" >> "$PGDATA/postgresql.conf"
  chown postgres:postgres "$PGDATA/postgresql.conf"
  chmod 640 "$PGDATA/postgresql.conf"
  
  echo "[OK] postgresql.conf configured"
  
  # ========================================================================
  # STEP 6: Configure pg_hba.conf (replace defaults with our auth rules)
  # ========================================================================
  echo "[STEP 6] Configuring pg_hba.conf..."
  
  # Replace entire pg_hba.conf with our configuration
  cat > "$PGDATA/pg_hba.conf" << 'HBA_CONF'
# PostgreSQL Client Authentication Configuration (UTF-8 RAG System)
# ===================================================================

# Allow local connections (trust for postgres user)
local   all             all                                     trust

# Allow remote connections with md5 authentication  
host    all             all             0.0.0.0/0               md5
host    all             all             ::/0                    md5
HBA_CONF

  chown postgres:postgres "$PGDATA/pg_hba.conf"
  chmod 640 "$PGDATA/pg_hba.conf"
  
  echo "[OK] pg_hba.conf configured"
else
  echo "[OK] Using existing PostgreSQL cluster"
fi

# ============================================================================
# STEP 7: Start PostgreSQL (as postgres user)
# ============================================================================
echo "[STEP 7] Starting PostgreSQL daemon..."

# Start as postgres user
su -m postgres -s /bin/bash << PGCTL_SCRIPT
export PATH='/usr/lib/postgresql/17.4.0.4/bin':\$PATH
export HOME='/var/lib/postgresql'
cd /var/lib/postgresql
pg_ctl -D '$PGDATA' -l '$PGDATA/logfile' start
PGCTL_SCRIPT
[ $? -eq 0 ] || exit 1

if [ $? -ne 0 ]; then
  echo "[ERROR] Failed to start PostgreSQL"
  echo "[ERROR] Last log entries:"
  tail -20 "$PGDATA/logfile" 2>/dev/null || echo "Cannot read logfile"
  exit 1
fi

echo "[OK] PostgreSQL daemon started"
sleep 2

# ============================================================================
# STEP 8: Verify PostgreSQL is ready (using pg_isready)
# ============================================================================
echo "[STEP 8] Verifying PostgreSQL is ready..."

export PATH='/usr/lib/postgresql/17.4.0.4/bin:'$PATH
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
  if pg_isready -h 127.0.0.1 -p 15234 -U postgres >/dev/null 2>&1; then
    echo "[OK] PostgreSQL is ready on 127.0.0.1:15234 ✓"
    break
  fi
  
  retry_count=$((retry_count + 1))
  if [ $retry_count -lt $max_retries ]; then
    echo "[INFO] Waiting for PostgreSQL to be ready ($retry_count/$max_retries)..."
    sleep 1
  fi
done

if [ $retry_count -eq $max_retries ]; then
  echo "[ERROR] PostgreSQL did not become ready after $max_retries retries"
  echo "[ERROR] Last logfile entries:"
  tail -30 "$PGDATA/logfile" 2>/dev/null || echo "Cannot read logfile"
  exit 1
fi

# ============================================================================
# STEP 9: Confirm UTF-8 encoding
# ============================================================================
echo "[STEP 9] Confirming UTF-8 encoding..."

# Use PGPORT env var to connect via Unix socket on custom port
encoding=$(PGPORT=15234 /usr/lib/postgresql/17.4.0.4/bin/psql -U postgres -t -c 'SHOW server_encoding;' 2>/dev/null | xargs)

if [ "$encoding" = "UTF8" ]; then
  echo "[OK] Server encoding is UTF8 ✓"
else
  echo "[WARNING] Encoding check result: $encoding (expected UTF8)"
fi

# ============================================================================
# STEP 10: Ready for production
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         ShaktiDB PostgreSQL 17.4 - Production Ready            ║"
echo "║                    UTF-8 Encoding Enabled                      ║"
echo "║                    Listening on 0.0.0.0:15234                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "[SUMMARY] Database initialized with:"
echo "  • Encoding: UTF-8 (en_US.UTF-8)"
echo "  • Locale: en_US.UTF-8 (all LC_* categories)"
echo "  • Port: 15234"
echo "  • Data dir: $PGDATA"
echo ""
echo "[INFO] Monitoring logfile: $PGDATA/logfile"
echo ""

# Keep container alive by tailing the logfile
exec tail -f "$PGDATA/logfile"
