#!/bin/bash
# Diagnostic script for Marshaall Suricata issues
echo "=== SURICATA STATUS ==="
ps aux | grep suricata | grep -v grep

echo ""
echo "=== INTERFACE & IPs ==="
ip -br addr show

echo ""
echo "=== DOCKER BRIDGE ==="
docker network inspect marshaall_backend_net 2>/dev/null | grep -E 'Subnet|Gateway' || echo 'network not found'

echo ""
echo "=== REAL ALERT COUNT IN EVE ==="
grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo "0 alerts or file not found"

echo ""
echo "=== EVE EVENT TYPES ==="
grep -oP '"event_type":"[^"]+"' /var/log/suricata/eve.json 2>/dev/null | sort | uniq -c | sort -rn | head -10

echo ""
echo "=== SURICATA RULES STATS ==="
grep -c "^alert " /etc/suricata/rules/local.rules 2>/dev/null || echo "no local.rules"

echo ""
echo "=== SURICATA LOG ERRORS ==="
tail -20 /var/log/suricata/suricata.log 2>/dev/null | grep -iE "error|warn|fail" || echo "no errors"

echo ""
echo "=== INGEST LOGS ==="
docker logs marshaall-ingest --tail 10 2>&1
