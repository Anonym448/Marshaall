#!/bin/bash
echo "=== DB: Event counts ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS total_events FROM events;
SELECT COUNT(*) AS total_alerts FROM events WHERE event_type = 'alert';
" 2>&1

echo ""
echo "=== DB: Alert summary by signature ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT signature_id, signature, COUNT(*) AS cnt, MAX(timestamp) AS last_seen
FROM events
WHERE event_type = 'alert'
GROUP BY signature_id, signature
ORDER BY last_seen DESC;
" 2>&1

echo ""
echo "=== DB: Latest 15 alerts ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT id, timestamp, src_ip, dest_ip, signature_id, LEFT(signature, 60) AS signature, severity
FROM events
WHERE event_type = 'alert'
ORDER BY id DESC
LIMIT 15;
" 2>&1
