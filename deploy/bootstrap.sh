#!/usr/bin/env bash
# One-paste server setup for Alibaba Cloud (Ubuntu, run as root).
# Usage:  export DASHSCOPE_API_KEY=sk-...   then:
#   curl -sL https://raw.githubusercontent.com/mark124/inspection-autopilot/main/deploy/bootstrap.sh | bash
set -euo pipefail

if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  echo "ERROR: run 'export DASHSCOPE_API_KEY=sk-...' first, then re-run this script."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io git curl
systemctl enable --now docker

rm -rf /opt/autopilot
git clone --depth 1 https://github.com/mark124/inspection-autopilot /opt/autopilot
cd /opt/autopilot
docker build -t autopilot .
docker rm -f autopilot 2>/dev/null || true
docker run -d --name autopilot --restart unless-stopped -p 8080:8080 \
  -e DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY" autopilot

sleep 4
echo "--- health check ---"
curl -s localhost:8080/api/health && echo
echo "--- public URL: http://$(curl -s ifconfig.me):8080 (open port 8080 in the firewall panel) ---"
