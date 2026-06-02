#!/bin/bash
echo "===== 1. DB EVENT TYPES ====="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT event_type, COUNT(*) AS cnt FROM events GROUP BY event_type ORDER BY cnt DESC;
SELECT COUNT(*) AS total FROM events;
SELECT COUNT(*) AS alerts FROM events WHERE event_type='alert';
"

echo ""
echo "===== 2. SURICATA FAST.LOG (last 20) ====="
docker exec marshaall-suricata tail -20 /var/log/suricata/fast.log 2>/dev/null || echo "(empty or not found)"

echo ""
echo "===== 3. SURICATA EVE.JSON alert count ====="
docker exec marshaall-suricata grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo "0"

echo ""
echo "===== 4. SURICATA EVE.JSON last 3 alerts ====="
docker exec marshaall-suricata grep '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null | tail -3

echo ""
echo "===== 5. SURICATA INTERFACES + NETWORK ====="
docker exec marshaall-suricata ip addr show 2>/dev/null || echo "ip not available"
echo "--- suricata process ---"
docker exec marshaall-suricata ps aux 2>/dev/null | grep suricata || echo "ps not available"

echo ""
echo "===== 6. SURICATA STATS (packets captured) ====="
docker exec marshaall-suricata grep -o '"kernel_packets":[0-9]*' /var/log/suricata/eve.json 2>/dev/null | tail -3

echo ""
echo "===== 7. DOCKER COMPOSE PS ====="
cd /home/user/marshaall
docker compose ps

echo ""
echo "===== 8. INGEST CODE (filter section) ====="
docker exec marshaall-ingest grep -A 5 "stats\|flow\|continue" /app/app.py 2>/dev/null | head -20

echo ""
echo "===== 9. INGEST LOGS ====="
docker compose logs --tail 10 ingest

echo ""
echo "===== 10. HOST NETWORK INTERFACES ====="
ip addr show eth0 | head -4
echo "---"
ip route | head -3
