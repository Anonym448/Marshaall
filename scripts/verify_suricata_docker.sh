#!/bin/bash
# Test ping and verify Suricata container detection
echo "=== Sending 3 pings ==="
ping -c 3 127.0.0.1

sleep 5

echo ""
echo "=== fast.log ICMP alerts ==="
docker exec marshaall-suricata cat /var/log/suricata/fast.log 2>/dev/null | grep -i icmp | tail -5
echo ""

echo "=== eve.json alert events ==="
docker exec marshaall-suricata cat /var/log/suricata/eve.json 2>/dev/null | grep '"event_type":"alert"' | tail -5
echo ""

echo "=== Ingest logs ==="
cd /home/user/marshaall
docker compose logs --tail 10 ingest
echo ""

echo "=== DB alert count ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS total_alerts FROM events WHERE event_type='alert';
SELECT id, signature, src_ip, dest_ip, ts FROM events WHERE event_type='alert' ORDER BY id DESC LIMIT 10;
"

echo "=== DONE ==="
