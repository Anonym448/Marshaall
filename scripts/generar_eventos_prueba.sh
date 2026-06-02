#!/bin/bash
# Script para generar eventos de prueba en Marshaall SIEM
# Uso: ./generar_eventos_prueba.sh [cantidad]

set -e

CANTIDAD=${1:-50}
EVE_FILE="/var/log/suricata/eve.json"
TEMP_FILE="/tmp/eventos_marshaall_$(date +%s).json"

echo "🚀 Generando $CANTIDAD eventos de prueba para Marshaall SIEM..."

# Tipos de alertas realistas
SIGNATURES=(
    "ET MALWARE Possible Trojan"
    "GPL SCAN nmap XMAS"
    "ET SCAN Potential SSH Scan"
    "ET WEB_SERVER SQL Injection Attempt"
    "ET POLICY Suspicious User-Agent"
    "ET EXPLOIT SMB Vulnerability"
    "ET DOS ICMP Flood"
    "ET MALWARE Ransomware Activity Detected"
    "ET ATTACK_RESPONSE SQL Error Message"
    "ET SCAN Nikto Scan in Progress"
    "GPL SSH brute force login attempt"
    "ET EXPLOIT Windows RDP Exploit Attempt"
    "ET MALWARE Command and Control Traffic"
    "ET WEB_SERVER PHP Injection Attempt"
    "ET POLICY External IP Lookup"
)

CATEGORIES=(
    "A Network Trojan was Detected"
    "Attempted Information Leak"
    "Web Application Attack"
    "Potentially Bad Traffic"
    "Attempted Administrator Privilege Gain"
    "Denial of Service"
    "Attempted User Privilege Gain"
)

PROTOCOLS=("TCP" "UDP" "ICMP")

# Generar eventos
for i in $(seq 1 $CANTIDAD); do
    # Timestamp actual con microsegundos
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N%z")
    
    # IPs aleatorias
    SRC_IP="192.168.1.$((RANDOM % 255 + 1))"
    DEST_IP="10.0.0.$((RANDOM % 255 + 1))"
    
    # Puertos aleatorios
    SRC_PORT=$((RANDOM % 65535 + 1))
    DEST_PORT=$((RANDOM % 65535 + 1))
    
    # Protocolo aleatorio
    PROTO=${PROTOCOLS[$((RANDOM % ${#PROTOCOLS[@]}))]}
    
    # Flow ID único
    FLOW_ID=$((RANDOM * RANDOM))
    
    # 70% alertas, 30% flows
    if [ $((RANDOM % 10)) -lt 7 ]; then
        # Generar alerta
        SIGNATURE=${SIGNATURES[$((RANDOM % ${#SIGNATURES[@]}))]}
        CATEGORY=${CATEGORIES[$((RANDOM % ${#CATEGORIES[@]}))]}
        SEVERITY=$((RANDOM % 3 + 1))
        
        cat >> "$TEMP_FILE" << EOF
{"timestamp":"$TIMESTAMP","event_type":"alert","src_ip":"$SRC_IP","dest_ip":"$DEST_IP","src_port":$SRC_PORT,"dest_port":$DEST_PORT,"proto":"$PROTO","flow_id":$FLOW_ID,"alert":{"signature":"$SIGNATURE","category":"$CATEGORY","severity":$SEVERITY}}
EOF
    else
        # Generar flow
        cat >> "$TEMP_FILE" << EOF
{"timestamp":"$TIMESTAMP","event_type":"flow","src_ip":"$SRC_IP","dest_ip":"$DEST_IP","src_port":$SRC_PORT,"dest_port":$DEST_PORT,"proto":"$PROTO","flow_id":$FLOW_ID}
EOF
    fi
    
    # Mostrar progreso cada 10 eventos
    if [ $((i % 10)) -eq 0 ]; then
        echo "  ✓ Generados $i/$CANTIDAD eventos..."
    fi
done

echo ""
echo "📝 Eventos generados en: $TEMP_FILE"
echo "📊 Total de eventos: $(wc -l < $TEMP_FILE)"

# Verificar si tenemos permisos para escribir en eve.json
if [ -w "$EVE_FILE" ]; then
    echo ""
    echo "✅ Inyectando eventos en $EVE_FILE..."
    cat "$TEMP_FILE" >> "$EVE_FILE"
    echo "✅ Eventos inyectados correctamente"
    rm "$TEMP_FILE"
else
    echo ""
    echo "⚠️  No tienes permisos para escribir en $EVE_FILE"
    echo "   Ejecuta con sudo o copia manualmente:"
    echo "   sudo cat $TEMP_FILE >> $EVE_FILE"
fi

echo ""
echo "🎯 Verifica los eventos en el dashboard: http://localhost"
echo "   Usuario: admin"
echo "   Contraseña: admin1234"
echo ""
echo "📈 Comandos útiles:"
echo "   - Ver logs de ingesta: docker logs -f marshaall-ingest --tail 50"
echo "   - Contar alertas: grep '\"event_type\":\"alert\"' $EVE_FILE | wc -l"
echo "   - Ver últimas alertas: grep '\"event_type\":\"alert\"' $EVE_FILE | tail -5 | jq ."
echo ""
