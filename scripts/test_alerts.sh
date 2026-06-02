#!/bin/bash
set -e

echo "============================================="
echo "  Marshaall — Test de generacion de alertas"
echo "============================================="
echo ""

# Esperamos un poco para que ingest termine de procesar el backlog
sleep 2

# Contamos alertas ANTES
ALERTS_BEFORE=$(grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo 0)
echo "[*] Alertas en eve.json ANTES de los tests: $ALERTS_BEFORE"
echo ""

echo "=== TEST 1: OpenVAS User-Agent ==="
curl -s -A "OpenVAS" http://localhost -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 2: Nessus User-Agent ==="
curl -s -A "Nessus" http://localhost -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 3: Nikto User-Agent ==="
curl -s -A "Nikto" http://localhost -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 4: Nmap Scripting Engine User-Agent ==="
curl -s -A "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)" http://localhost -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 5: Intento de descarga EICAR ==="
curl -s http://www.eicar.org/download/eicar.com -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo, puede estar bloqueado)"
sleep 1

echo "=== TEST 6: Acceso a /wp-admin ==="
curl -s http://localhost/wp-admin -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 7: Acceso a /phpmyadmin ==="
curl -s http://localhost/phpmyadmin -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 8: Acceso a /.env ==="
curl -s http://localhost/.env -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 1

echo "=== TEST 9: Nuclei User-Agent ==="
curl -s -A "Nuclei" http://localhost -o /dev/null -w "HTTP %{http_code}\n" 2>/dev/null || echo "(curl fallo)"
sleep 3

echo ""
echo "=== RESULTADOS ==="
ALERTS_AFTER=$(grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo 0)
NEW_ALERTS=$((ALERTS_AFTER - ALERTS_BEFORE))
echo "[*] Alertas en eve.json DESPUES de los tests: $ALERTS_AFTER"
echo "[*] NUEVAS alertas generadas: $NEW_ALERTS"
echo ""

if [ "$NEW_ALERTS" -gt 0 ]; then
    echo "[+] Las nuevas alertas:"
    grep '"event_type":"alert"' /var/log/suricata/eve.json | tail -"$NEW_ALERTS" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        a = e.get('alert', {})
        print(f'  SID:{a.get(\"signature_id\",\"?\")} sev:{a.get(\"severity\",\"?\")} | {a.get(\"signature\",\"?\")} | {e.get(\"src_ip\",\"?\")} -> {e.get(\"dest_ip\",\"?\")}')
    except:
        pass
" 2>/dev/null
else
    echo "[-] No se generaron nuevas alertas. Revisar config de Suricata."
fi
