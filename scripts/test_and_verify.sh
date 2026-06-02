#!/bin/bash
set -e

echo "=== 1. Restart ingest with new code ==="
cd /home/user/marshaall
docker compose up -d --build ingest
sleep 5

echo "=== 2. Truncate DB ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SET FOREIGN_KEY_CHECKS=0;
TRUNCATE TABLE alert_status;
TRUNCATE TABLE events;
SET FOREIGN_KEY_CHECKS=1;
SELECT 'DB truncated OK' AS status;
"

echo "=== 3. Reset eve.json offset ==="
# Force ingest to re-read from current position
docker compose restart ingest
sleep 5

echo "=== 4. Test: ping localhost ==="
ping -c 3 127.0.0.1
sleep 5

echo "=== 5. Check fast.log for ICMP ==="
echo "--- Last 10 lines of fast.log ---"
tail -10 /var/log/suricata/fast.log

echo ""
echo "=== 6. Check ingest logs ==="
docker compose logs --tail 20 ingest

echo ""
echo "=== 7. Check DB for alerts ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS total_events FROM events;
SELECT COUNT(*) AS total_alerts FROM events WHERE event_type='alert';
SELECT id, event_type, signature, severity, src_ip, dest_ip, ts
FROM events WHERE event_type='alert' ORDER BY id DESC LIMIT 10;
"

echo "=== ALL DONE ==="
