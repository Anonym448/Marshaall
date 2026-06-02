#!/bin/bash
# Force kill all old Suricata processes, keep only newest
echo "Force killing ALL suricata PIDs..."
for pid in $(pgrep suricata); do
    sudo kill -9 "$pid" 2>/dev/null
    echo "  killed PID $pid"
done
sleep 2
sudo rm -f /var/run/suricata.pid /run/suricata.pid

echo "Verifying rules file..."
cat /var/lib/suricata/rules/local.rules
echo ""
echo "Starting fresh Suricata..."
sudo suricata --pcap=lo -k none -D
sleep 3

echo "=== Running process ==="
ps aux | grep '[s]uricata'
echo "=== suricata.log last 10 ==="
tail -10 /var/log/suricata/suricata.log
echo "=== DONE ==="
