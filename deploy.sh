#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NestAI deploy script — Oracle Cloud Always-Free (Ubuntu 22.04 ARM)
#
# First run:   ./deploy.sh https://github.com/youruser/nestai.git
# Updates:     ./deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/opt/nestai"
COMPOSE="docker compose -f $APP_DIR/docker/docker-compose.prod.yml"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
die()  { echo -e "${RED}✗ $*${NC}"; exit 1; }

echo -e "${GREEN}"
echo "  ███╗   ██╗███████╗███████╗████████╗ █████╗ ██╗"
echo "  ████╗  ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██║"
echo "  ██╔██╗ ██║█████╗  ███████╗   ██║   ███████║██║"
echo "  ██║╚██╗██║██╔══╝  ╚════██║   ██║   ██╔══██║██║"
echo "  ██║ ╚████║███████╗███████║   ██║   ██║  ██║██║"
echo "  ╚═╝  ╚═══╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝"
echo -e "${NC}"

# ── Step 1: Install Docker if missing ────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    warn "Docker not found — installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    ok "Docker installed. Log out, log back in, then re-run: ./deploy.sh"
    exit 0
fi
ok "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+')"

# ── Step 2: Open Oracle host firewall (iptables) ──────────────────────────────
echo "Configuring host firewall..."
for PORT in 80 9000; do
    if ! sudo iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null; then
        sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$PORT" -j ACCEPT
    fi
done
# Persist rules across reboots
if command -v netfilter-persistent &>/dev/null; then
    sudo netfilter-persistent save 2>/dev/null || true
elif command -v iptables-save &>/dev/null; then
    sudo mkdir -p /etc/iptables
    sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null
fi
ok "Firewall: ports 80 (HTTP) and 9000 (MinIO) open"

# ── Step 3: Clone repo or pull latest ────────────────────────────────────────
if [ ! -d "$APP_DIR/.git" ]; then
    REPO=${1:-}
    [ -z "$REPO" ] && die "First run requires repo URL: ./deploy.sh https://github.com/you/nestai.git"
    sudo git clone "$REPO" "$APP_DIR"
    sudo chown -R "$USER:$USER" "$APP_DIR"
    ok "Repo cloned → $APP_DIR"
else
    cd "$APP_DIR"
    git pull
    ok "Repo updated → $(git rev-parse --short HEAD)"
fi
cd "$APP_DIR"

# ── Step 4: Create .env on first run ─────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.prod.example .env
    # Auto-fill public IP
    PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "YOUR_ORACLE_PUBLIC_IP")
    sed -i "s/YOUR_ORACLE_PUBLIC_IP/$PUBLIC_IP/g" .env
    echo ""
    warn "Created .env — you must fill in your API keys before continuing:"
    echo ""
    echo "    nano $APP_DIR/.env"
    echo ""
    echo "  Required:"
    echo "    POSTGRES_PASSWORD   — any strong password"
    echo "    MINIO_ROOT_PASSWORD — any strong password"
    echo "    JWT_SECRET          — run: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo "    OPENAI_API_KEY      — from platform.openai.com"
    echo "    ANTHROPIC_API_KEY   — from console.anthropic.com"
    echo ""
    warn "Then re-run: ./deploy.sh"
    exit 0
fi
ok ".env found"

# Validate no CHANGE_ME placeholders remain
if grep -q "CHANGE_ME" .env; then
    die ".env still contains CHANGE_ME placeholders — fill them in first."
fi

# Load env vars for use in this script
set -a; source .env; set +a

# ── Step 5: Build Docker images ───────────────────────────────────────────────
echo "Building images (3–5 min on first run)..."
$COMPOSE build
ok "Images built"

# ── Step 6: Start DB + Redis + MinIO first ────────────────────────────────────
echo "Starting core services..."
$COMPOSE up -d db redis minio
echo -n "Waiting for DB to be healthy"
for i in $(seq 1 30); do
    if $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" &>/dev/null; then
        echo ""; ok "Database ready"; break
    fi
    echo -n "."; sleep 2
done

# ── Step 7: Init MinIO buckets (safe to run multiple times) ───────────────────
echo "Initialising MinIO buckets..."
$COMPOSE --profile init run --rm minio-init 2>/dev/null || true
ok "MinIO buckets ready"

# ── Step 8: Apply DB migrations ───────────────────────────────────────────────
echo "Applying migrations..."
$COMPOSE run --rm --no-deps api python3 -c "
import asyncio, os, asyncpg

async def run():
    url = os.environ['DATABASE_URL'].replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    sql = open('/app/migrations/init.sql').read()
    await conn.execute(sql)
    await conn.close()

asyncio.run(run())
print('Migrations applied.')
"
ok "Migrations applied"

# ── Step 9: Seed database (first run only) ────────────────────────────────────
SEED_FLAG="$APP_DIR/.seeded"
if [ ! -f "$SEED_FLAG" ]; then
    echo "Seeding database..."
    $COMPOSE run --rm --no-deps api python3 -c "
import asyncio, os, asyncpg, pathlib

async def run():
    url = os.environ['DATABASE_URL'].replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    seed_dir = pathlib.Path('/app/seed')
    for f in sorted(seed_dir.glob('*.sql')):
        print(f'  Seeding {f.name}...')
        await conn.execute(f.read_text())
    await conn.close()

asyncio.run(run())
print('Seed complete.')
" 2>/dev/null || warn "Seed failed or already applied — continuing"
    touch "$SEED_FLAG"
    ok "Database seeded"
fi

# ── Step 10: Start all services ───────────────────────────────────────────────
echo "Starting all services..."
$COMPOSE up -d
ok "All services started"

# ── Done ─────────────────────────────────────────────────────────────────────
PUBLIC_IP=$(grep "^FRONTEND_URL" .env | cut -d= -f2 | sed 's|http://||' | cut -d: -f1)
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  NestAI is live!${NC}"
echo -e ""
echo -e "  Frontend  →  http://$PUBLIC_IP"
echo -e "  API docs  →  http://$PUBLIC_IP/docs  (via nginx proxy)"
echo -e "  Storage   →  http://$PUBLIC_IP:9000"
echo -e ""
echo -e "  To watch logs:  docker compose -f docker/docker-compose.prod.yml logs -f"
echo -e "  To update:      git pull && ./deploy.sh"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
$COMPOSE ps
