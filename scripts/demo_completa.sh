#!/bin/bash
# Script de demostración completa del sistema Marshaall SIEM
# Genera eventos, verifica el sistema y muestra estadísticas

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║  ${CYAN}🛡️  MARSHAALL SIEM - DEMOSTRACIÓN COMPLETA${BLUE}  🛡️          ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Este script demostrará el funcionamiento completo del SIEM:${NC}"
echo "  1. Verificación del sistema"
echo "  2. Generación de eventos de prueba"
echo "  3. Visualización de estadísticas"
echo "  4. Acceso al dashboard"
echo ""
read -p "Presiona ENTER para continuar..."

# ============================================================================
# PASO 1: VERIFICACIÓN DEL SISTEMA
# ============================================================================

echo ""
echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  PASO 1: VERIFICACIÓN DEL SISTEMA                         ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar Suricata
echo -e "${CYAN}[1/5]${NC} Verificando Suricata..."
if command -v suricata &> /dev/null && pgrep -x suricata > /dev/null; then
    echo -e "${GREEN}✓ Suricata está corriendo${NC}"
else
    echo -e "${YELLOW}⚠ Suricata no está corriendo. Iniciando...${NC}"
    sudo systemctl start suricata 2>/dev/null || echo -e "${RED}✗ No se pudo iniciar Suricata${NC}"
fi

# Verificar Docker
echo -e "${CYAN}[2/5]${NC} Verificando contenedores Docker..."
RUNNING=$(docker ps --filter "name=marshaall" --format "{{.Names}}" | wc -l)
if [ "$RUNNING" -eq 4 ]; then
    echo -e "${GREEN}✓ Todos los contenedores están corriendo ($RUNNING/4)${NC}"
else
    echo -e "${YELLOW}⚠ Solo $RUNNING/4 contenedores corriendo${NC}"
fi

# Verificar API
echo -e "${CYAN}[3/5]${NC} Verificando API..."
if curl -s http://localhost/api/health | grep -q '"api":"ok"'; then
    echo -e "${GREEN}✓ API respondiendo correctamente${NC}"
else
    echo -e "${RED}✗ API no responde${NC}"
fi

# Verificar archivo EVE JSON
echo -e "${CYAN}[4/5]${NC} Verificando archivo EVE JSON..."
EVE_FILE="/var/log/suricata/eve.json"
if [ -f "$EVE_FILE" ]; then
    SIZE=$(du -h "$EVE_FILE" | cut -f1)
    echo -e "${GREEN}✓ Archivo EVE JSON existe (tamaño: $SIZE)${NC}"
else
    echo -e "${RED}✗ Archivo EVE JSON no encontrado${NC}"
fi

# Contar eventos actuales
echo -e "${CYAN}[5/5]${NC} Contando eventos actuales..."
EVENTOS_ANTES=$(grep -c '"event_type"' "$EVE_FILE" 2>/dev/null || echo "0")
ALERTAS_ANTES=$(grep -c '"event_type":"alert"' "$EVE_FILE" 2>/dev/null || echo "0")
echo -e "${YELLOW}  Eventos totales: $EVENTOS_ANTES${NC}"
echo -e "${YELLOW}  Alertas: $ALERTAS_ANTES${NC}"

echo ""
read -p "Presiona ENTER para continuar con la generación de eventos..."

# ============================================================================
# PASO 2: GENERACIÓN DE EVENTOS
# ============================================================================

echo ""
echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  PASO 2: GENERACIÓN DE EVENTOS DE PRUEBA                  ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

CANTIDAD=50
echo -e "${CYAN}Generando $CANTIDAD eventos de prueba...${NC}"
echo ""

# Generar eventos
TEMP_FILE="/tmp/demo_eventos_$(date +%s).json"

SIGNATURES=(
    "ET MALWARE Possible Trojan"
    "GPL SCAN nmap XMAS"
    "ET SCAN Potential SSH Scan"
    "ET WEB_SERVER SQL Injection Attempt"
    "ET POLICY Suspicious User-Agent"
    "ET EXPLOIT SMB Vulnerability"
    "ET DOS ICMP Flood"
    "ET MALWARE Ransomware Activity Detected"
)

CATEGORIES=(
    "A Network Trojan was Detected"
    "Attempted Information Leak"
    "Web Application Attack"
    "Potentially Bad Traffic"
    "Attempted Administrator Privilege Gain"
    "Denial of Service"
)

for i in $(seq 1 $CANTIDAD); do
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N%z")
    SRC_IP="192.168.1.$((RANDOM % 255 + 1))"
    DEST_IP="10.0.0.$((RANDOM % 255 + 1))"
    SRC_PORT=$((RANDOM % 65535 + 1))
    DEST_PORT=$((RANDOM % 65535 + 1))
    FLOW_ID=$((RANDOM * RANDOM))
    
    if [ $((RANDOM % 10)) -lt 7 ]; then
        SIGNATURE=${SIGNATURES[$((RANDOM % ${#SIGNATURES[@]}))]}
        CATEGORY=${CATEGORIES[$((RANDOM % ${#CATEGORIES[@]}))]}
        SEVERITY=$((RANDOM % 3 + 1))
        
        echo "{\"timestamp\":\"$TIMESTAMP\",\"event_type\":\"alert\",\"src_ip\":\"$SRC_IP\",\"dest_ip\":\"$DEST_IP\",\"src_port\":$SRC_PORT,\"dest_port\":$DEST_PORT,\"proto\":\"TCP\",\"flow_id\":$FLOW_ID,\"alert\":{\"signature\":\"$SIGNATURE\",\"category\":\"$CATEGORY\",\"severity\":$SEVERITY}}" >> "$TEMP_FILE"
    else
        echo "{\"timestamp\":\"$TIMESTAMP\",\"event_type\":\"flow\",\"src_ip\":\"$SRC_IP\",\"dest_ip\":\"$DEST_IP\",\"src_port\":$SRC_PORT,\"dest_port\":$DEST_PORT,\"proto\":\"TCP\",\"flow_id\":$FLOW_ID}" >> "$TEMP_FILE"
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        echo -e "${GREEN}  ✓ Generados $i/$CANTIDAD eventos...${NC}"
    fi
done

echo ""
echo -e "${CYAN}Inyectando eventos en el sistema...${NC}"
sudo cat "$TEMP_FILE" >> "$EVE_FILE"
rm "$TEMP_FILE"

echo -e "${GREEN}✓ $CANTIDAD eventos inyectados correctamente${NC}"
echo ""
echo -e "${YELLOW}Esperando 5 segundos para que el servicio de ingesta procese...${NC}"
sleep 5

# ============================================================================
# PASO 3: ESTADÍSTICAS
# ============================================================================

echo ""
echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  PASO 3: ESTADÍSTICAS DEL SISTEMA                         ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Contar eventos después
EVENTOS_DESPUES=$(grep -c '"event_type"' "$EVE_FILE" 2>/dev/null || echo "0")
ALERTAS_DESPUES=$(grep -c '"event_type":"alert"' "$EVE_FILE" 2>/dev/null || echo "0")

EVENTOS_NUEVOS=$((EVENTOS_DESPUES - EVENTOS_ANTES))
ALERTAS_NUEVAS=$((ALERTAS_DESPUES - ALERTAS_ANTES))

echo -e "${CYAN}📊 Resumen de eventos:${NC}"
echo ""
echo -e "  Eventos antes:     ${YELLOW}$EVENTOS_ANTES${NC}"
echo -e "  Eventos después:   ${YELLOW}$EVENTOS_DESPUES${NC}"
echo -e "  ${GREEN}Nuevos eventos:    +$EVENTOS_NUEVOS${NC}"
echo ""
echo -e "  Alertas antes:     ${YELLOW}$ALERTAS_ANTES${NC}"
echo -e "  Alertas después:   ${YELLOW}$ALERTAS_DESPUES${NC}"
echo -e "  ${GREEN}Nuevas alertas:    +$ALERTAS_NUEVAS${NC}"
echo ""

# Top 5 firmas
echo -e "${CYAN}🔝 Top 5 firmas de alertas:${NC}"
echo ""
grep '"event_type":"alert"' "$EVE_FILE" 2>/dev/null | \
    grep -o '"signature":"[^"]*"' | \
    cut -d'"' -f4 | \
    sort | uniq -c | sort -rn | head -5 | \
    while read count signature; do
        echo -e "  ${YELLOW}$count${NC} × $signature"
    done

echo ""

# Top 5 IPs origen
echo -e "${CYAN}🌐 Top 5 IPs origen de alertas:${NC}"
echo ""
grep '"event_type":"alert"' "$EVE_FILE" 2>/dev/null | \
    grep -o '"src_ip":"[^"]*"' | \
    cut -d'"' -f4 | \
    sort | uniq -c | sort -rn | head -5 | \
    while read count ip; do
        echo -e "  ${YELLOW}$count${NC} × $ip"
    done

echo ""

# Logs de ingesta
echo -e "${CYAN}📝 Últimos logs del servicio de ingesta:${NC}"
echo ""
docker logs marshaall-ingest --tail 5 2>&1 | grep "Batch:" | tail -3 | while read line; do
    echo -e "  ${GREEN}$line${NC}"
done

# ============================================================================
# PASO 4: ACCESO AL DASHBOARD
# ============================================================================

echo ""
echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  PASO 4: ACCESO AL DASHBOARD                              ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

HOST_IP=$(hostname -I | awk '{print $1}')

echo -e "${CYAN}🌐 Dashboard disponible en:${NC}"
echo ""
echo -e "  ${GREEN}http://localhost${NC}"
echo -e "  ${GREEN}http://$HOST_IP${NC}"
echo ""
echo -e "${CYAN}🔑 Credenciales:${NC}"
echo ""
echo -e "  Usuario:    ${YELLOW}admin${NC}"
echo -e "  Contraseña: ${YELLOW}admin1234${NC}"
echo ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ✅ DEMOSTRACIÓN COMPLETADA                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📊 Qué puedes hacer ahora:${NC}"
echo ""
echo "  1. Abre el dashboard en tu navegador"
echo "  2. Ve a la sección 'Dashboard' para ver gráficos"
echo "  3. Explora 'Alertas' para ver las alertas generadas"
echo "  4. Crea un 'Incidente' agrupando alertas relacionadas"
echo "  5. Genera un 'Reporte XML' para auditoría"
echo ""
echo -e "${YELLOW}🔥 Para generar tráfico real desde Kali Linux:${NC}"
echo ""
echo "  1. Copia el script a Kali:"
echo -e "     ${GREEN}scp scripts/kali_ataques.sh kali@<IP_KALI>:~/${NC}"
echo ""
echo "  2. Ejecuta desde Kali:"
echo -e "     ${GREEN}chmod +x kali_ataques.sh${NC}"
echo -e "     ${GREEN}sudo ./kali_ataques.sh $HOST_IP${NC}"
echo ""
echo -e "${YELLOW}📚 Documentación:${NC}"
echo ""
echo "  • Guía completa: docs/GUIA_GENERACION_ALERTAS.md"
echo "  • Guía rápida:   docs/QUICKSTART_ALERTAS.md"
echo "  • Resumen:       docs/RESUMEN_ALERTAS.md"
echo ""
echo -e "${GREEN}¡Gracias por usar Marshaall SIEM!${NC} 🛡️"
echo ""
