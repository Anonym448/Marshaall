#!/bin/bash
# Kill all suricata instances, restart fresh
echo "Killing all Suricata instances..."
sudo killall -9 suricata 2>/dev/null
sleep 2
sudo rm -f /var/run/suricata.pid /run/suricata.pid
echo "Starting Suricata with new rules..."
sudo suricata --pcap=lo -k none -D
sleep 3
echo "--- Suricata process ---"
ps aux | grep '[s]uricata'
echo "--- Rules loaded ---"
grep -c 'sid:' /var/lib/suricata/rules/local.rules
echo "--- fast.log tail ---"
tail -3 /var/log/suricata/fast.log 2>/dev/null || echo "(empty)"
echo "--- Restarting ingest ---"
cd /home/user/marshaall
docker compose restart ingest
sleep 3
echo "--- Ingest status ---"
docker compose ps ingest
echo "DONE"
