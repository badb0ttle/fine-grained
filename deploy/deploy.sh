#!/bin/bash
# Deploy AllOfAI API to ECS production
# Run this as root on the EC...: .venv        # Python venv (already exists from pipeline)
#
# Usage: bash deploy.sh [--dry-run]

set -euo pipefail
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; shift; fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
run() {
    echo -e "${GREEN}→${NC} $*"
    if [ $DRY_RUN -eq 0 ]; then eval "$*"; fi
}

BASE="/root/fine-grained"
echo "🚀 Deploying AllOfAI API to $BASE"

# ── 1. Install API deps ──
echo ""
echo "── 1. Python dependencies ──"
run "$BASE/.venv/bin/pip install fastapi uvicorn[standard] python-dotenv"
# Pipeline deps (already installed but verify)
run "$BASE/.venv/bin/pip install numpy scikit-learn requests"

# ── 2. Generate API key if not set ──
echo ""
echo "── 2. API key ──"
if ! grep -q "AI_INTEL_API_KEY=crn_" "$BASE/.env" 2>/dev/null; then
    NEW_KEY=***"_"$(python3 -c "import secrets; print(secrets.token_hex(16))")
    echo -e "${YELLOW}⚠️  Generating new API key${NC}"
    if [ $DRY_RUN -eq 0 ]; then
        echo "AI_INTEL_API_KEY=$NEW_KEY" >> "$BASE/.env"
    fi
    echo "   Key: $NEW_KEY"
fi

# ── 3. Test import ──
echo ""
echo "── 3. Verify imports ──"
run "$BASE/.venv/bin/python3 -c 'from api.main import app; print(\"✅ API imports OK\")'"

# ── 4. Quick health check ──
echo ""
echo "── 4. Quick health check ──"
if [ $DRY_RUN -eq 0 ]; then
    # Start API briefly to test
    "$BASE/.venv/bin/python3" -c "
import sys, os
os.chdir('$BASE')
from api.main import app
from api.db import check_db_health
h = check_db_health()
print(f'DB: {h[\"status\"]} — {h[\"article_count\"]} articles, {len(h[\"tables\"])} tables')
" || echo -e "${RED}⚠ DB health check failed${NC}"
fi

# ── 5. Install systemd service ──
echo ""
echo "── 5. Install systemd ──"
SERVICE_FILE="/etc/systemd/system/ai-intel-api.service"
if [ -f "$BASE/deploy/ai-intel-api.service" ]; then
    run "cp $BASE/deploy/ai-intel-api.service $SERVICE_FILE"
    run "systemctl daemon-reload"
    run "systemctl enable ai-intel-api"
    run "systemctl restart ai-intel-api"
    sleep 2
    if [ $DRY_RUN -eq 0 ]; then
        systemctl is-active ai-intel-api && echo "✅ Service running" || echo -e "${RED}⚠ Service not running${NC}"
    fi
else
    echo -e "${YELLOW}⚠ deploy/ai-intel-api.service not found — skipping${NC}"
fi

# ── 6. Configure OpenResty ──
echo ""
echo "── 6. OpenResty proxy ──"
NGINX_SITES="/usr/local/openresty/nginx/conf/sites"
if [ -d "$NGINX_SITES" ]; then
    if [ -f "$BASE/deploy/ai-intel-api.conf" ]; then
        run "cp $BASE/deploy/ai-intel-api.conf $NGINX_SITES/"
        run "openresty -t 2>/dev/null || nginx -t"
        run "openresty -s reload 2>/dev/null || nginx -s reload"
        echo "✅ OpenResty reloaded"
    else
        echo -e "${YELLOW}⚠ deploy/ai-intel-api.conf not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ OpenResty sites dir not found at $NGINX_SITES — skip${NC}"
fi

# ── 7. Test API ──
echo ""
echo "── 7. Smoke test ──"
run "sleep 2 && curl -sf http://127.0.0.1:8001/health | python3 -m json.tool 2>/dev/null || echo 'API not reachable yet'"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "API: http://127.0.0.1:8001 (internal) / https://ai.hjhai.xyz/api (public)"
echo "Status: sudo systemctl status ai-intel-api"
echo "Logs:   sudo journalctl -u ai-intel-api -f"
