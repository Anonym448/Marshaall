#!/bin/bash
set -e

echo "=== 1. Copiar reglas al sistema ==="
sudo cp /home/user/marshaall/suricata/local.rules /var/lib/suricata/rules/local.rules
echo "Reglas copiadas a /var/lib/suricata/rules/local.rules"
cat /var/lib/suricata/rules/local.rules | grep "^alert" | wc -l
echo "reglas activas"

echo ""
echo "=== 2. Reiniciar Suricata (pcap lo, -k none) ==="
sudo pkill -9 suricata 2>/dev/null || true
sudo rm -f /run/suricata.pid
sleep 3
sudo suricata --pcap=lo -c /etc/suricata/suricata.yaml -D --pidfile /run/suricata.pid -k none 2>&1
sleep 5

if pgrep suricata > /dev/null; then
    PID=$(cat /run/suricata.pid 2>/dev/null)
    echo "Suricata RUNNING (PID: $PID)"
    grep "rules successfully loaded" /var/log/suricata/suricata.log | tail -1
else
    echo "ERROR: Suricata no arrancó"
    tail -10 /var/log/suricata/suricata.log
    exit 1
fi

echo ""
echo "=== 3. Reiniciar ingest (resetear offset) ==="
cd /home/user/marshaall
docker compose restart ingest 2>&1
sleep 5
docker logs marshaall-ingest --tail 3 2>&1
