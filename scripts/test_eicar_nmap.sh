#!/bin/bash
echo "============================================="
echo "  Marshaall — Tests EICAR + Nmap"
echo "============================================="

BEFORE=$(grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo 0)
echo "Alertas eve.json ANTES: $BEFORE"
echo ""

# --- TEST 1: EICAR ---
echo "=== TEST 1: Descarga EICAR ==="
curl -s http://www.eicar.org/download/eicar.com -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(fallo)"
sleep 2

# --- TEST 2: Nmap SYN Scan ---
echo "=== TEST 2: Nmap SYN Scan (-sS) puertos 1-100 ==="
nmap -sS -p 1-100 localhost 2>&1 | tail -3
sleep 3

# --- TEST 3: Nmap XMAS Scan ---
echo "=== TEST 3: Nmap XMAS Scan (-sX) puertos 80,443 ==="
nmap -sX -p 80,443 localhost 2>&1 | tail -3
sleep 3

# --- TEST 4: Nmap NULL Scan ---
echo "=== TEST 4: Nmap NULL Scan (-sN) puertos 80,443 ==="
nmap -sN -p 80,443 localhost 2>&1 | tail -3
sleep 3

# --- TEST 5: Nmap FIN Scan ---
echo "=== TEST 5: Nmap FIN Scan (-sF) puertos 80,443 ==="
nmap -sF -p 80,443 localhost 2>&1 | tail -3
sleep 3

echo ""
echo "============================================="
echo "  RESULTADOS"
echo "============================================="
AFTER=$(grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo 0)
NEW=$((AFTER - BEFORE))
echo "Alertas eve.json DESPUES: $AFTER"
echo "NUEVAS alertas: $NEW"
echo ""

if [ "$NEW" -gt 0 ]; then
    echo "=== Nuevas alertas (fast.log) ==="
    tail -"$NEW" /var/log/suricata/fast.log 2>/dev/null | head -20
    echo ""
    echo "=== Nuevas alertas (eve.json detalle) ==="
    grep '"event_type":"alert"' /var/log/suricata/eve.json | tail -"$NEW" | python3 -c '
import sys, json
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        a = e.get("alert", {})
        ts = e.get("timestamp", "?")[:19]
        sid = a.get("signature_id", "?")
        sig = a.get("signature", "?")
        src = e.get("src_ip", "?")
        dst = e.get("dest_ip", "?")
        print(f"  {ts} SID:{sid} | {sig} | {src} -> {dst}")
    except:
        pass
' 2>/dev/null
else
    echo "NO se generaron alertas nuevas."
fi

echo ""
echo "=== BD: Alertas recientes ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS total_alerts FROM events WHERE event_type='alert';
SELECT id, ts, src_ip, dest_ip, LEFT(signature,60) AS signature, severity
FROM events WHERE event_type='alert' ORDER BY id DESC LIMIT 10;
" 2>&1
