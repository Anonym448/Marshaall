#!/bin/bash
# Script de verificación del sistema Marshaall SIEM
# Verifica que todos los componentes estén funcionando correctamente

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🔍 MARSHAALL SIEM - VERIFICACIÓN DEL SISTEMA            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Verificar Suricata
echo -e "${BLUE}[1/7]${NC} Verificando Suricata..."
if command -v suricata &> /dev/null; then
    echo -e "${GREEN}✓ Suricata instalado: $(suricata --version | head -1)${NC}"
    
    if pgrep -x suricata > /dev/null; then
        echo -e "${GREEN}✓ Suricata está corriendo${NC}"
    else
        echo -e "${YELLOW}⚠ Suricata NO está corriendo${NC}"
        echo -e "${YELLOW}  Ejecuta: sudo systemctl start suricata${NC}"
    fi
else
    echo -e "${RED}✗ Suricata NO instalado${NC}"
fi

# 2. Verificar archivo EVE JSON
echo ""
echo -e "${BLUE}[2/7]${NC} Verificando archivo EVE JSON..."
EVE_FILE="/var/log/suricata/eve.json"
if [ -f "$EVE_FILE" ]; then
    SIZE=$(du -h "$EVE_FILE" | cut -f1)
    LINES=$(wc -l < "$EVE_FILE")
    echo -e "${GREEN}✓ Archivo EVE JSON existe${NC}"
    echo -e "  Tamaño: $SIZE"
    echo -e "  Líneas: $LINES"
    
    # Contar eventos por tipo
    ALERTS=$(grep -c '"event_type":"alert"' "$EVE_FILE" 2>/dev/null || echo "0")
    FLOWS=$(grep -c '"event_type":"flow"' "$EVE_FILE" 2>/dev/null || echo "0")
    echo -e "  Alertas: ${YELLOW}$ALERTS${NC}"
    echo -e "  Flows: ${YELLOW}$FLOWS${NC}"
else
    echo -e "${RED}✗ Archivo EVE JSON NO existe${NC}"
fi

# 3. Verificar contenedores Docker
echo ""
echo -e "${BLUE}[3/7]${NC} Verificando contenedores Docker..."
if command -v docker &> /dev/null; then
    CONTAINERS=("marshaall-mariadb" "marshaall-ingest" "marshaall-backend" "marshaall-nginx")
    ALL_OK=true
    
    for container in "${CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$container")
            if [ "$STATUS" == "running" ]; then
                echo -e "${GREEN}✓ $container: running${NC}"
            else
                echo -e "${RED}✗ $container: $STATUS${NC}"
                ALL_OK=false
            fi
        else
            echo -e "${RED}✗ $container: no encontrado${NC}"
            ALL_OK=false
        fi
    done
    
    if [ "$ALL_OK" = true ]; then
        echo -e "${GREEN}✓ Todos los contenedores están corriendo${NC}"
    else
        echo -e "${YELLOW}⚠ Algunos contenedores tienen problemas${NC}"
        echo -e "${YELLOW}  Ejecuta: docker compose up -d${NC}"
    fi
else
    echo -e "${RED}✗ Docker NO instalado${NC}"
fi

# 4. Verificar API
echo ""
echo -e "${BLUE}[4/7]${NC} Verificando API..."
if command -v curl &> /dev/null; then
    HEALTH=$(curl -s http://localhost/api/health 2>/dev/null)
    if [ -n "$HEALTH" ]; then
        echo -e "${GREEN}✓ API respondiendo${NC}"
        
        API_STATUS=$(echo "$HEALTH" | grep -o '"api":"[^"]*"' | cut -d'"' -f4)
        DB_STATUS=$(echo "$HEALTH" | grep -o '"db":"[^"]*"' | cut -d'"' -f4)
        INGEST_STATUS=$(echo "$HEALTH" | grep -o '"ingest":"[^"]*"' | cut -d'"' -f4)
        
        echo -e "  API: ${GREEN}$API_STATUS${NC}"
        echo -e "  DB: ${GREEN}$DB_STATUS${NC}"
        echo -e "  Ingesta: ${YELLOW}$INGEST_STATUS${NC}"
    else
        echo -e "${RED}✗ API NO responde${NC}"
    fi
else
    echo -e "${YELLOW}⚠ curl no instalado, no se puede verificar API${NC}"
fi

# 5. Verificar base de datos
echo ""
echo -e "${BLUE}[5/7]${NC} Verificando base de datos..."
if docker exec marshaall-mariadb mysql -u marshaall -p"${MYSQL_PASSWORD:-marshaall123}" -e "USE marshaall; SELECT COUNT(*) FROM events;" 2>/dev/null | tail -1 > /tmp/event_count.txt 2>&1; then
    EVENT_COUNT=$(cat /tmp/event_count.txt)
    echo -e "${GREEN}✓ Base de datos accesible${NC}"
    echo -e "  Eventos en BD: ${YELLOW}$EVENT_COUNT${NC}"
    rm -f /tmp/event_count.txt
else
    echo -e "${YELLOW}⚠ No se pudo conectar a la base de datos${NC}"
fi

# 6. Verificar logs de ingesta
echo ""
echo -e "${BLUE}[6/7]${NC} Verificando servicio de ingesta..."
INGEST_LOGS=$(docker logs marshaall-ingest --tail 10 2>&1)
if echo "$INGEST_LOGS" | grep -q "Batch:"; then
    LAST_BATCH=$(echo "$INGEST_LOGS" | grep "Batch:" | tail -1)
    echo -e "${GREEN}✓ Servicio de ingesta activo${NC}"
    echo -e "  Último batch: ${YELLOW}$LAST_BATCH${NC}"
else
    echo -e "${YELLOW}⚠ No se detecta actividad reciente en ingesta${NC}"
fi

# 7. Verificar frontend
echo ""
echo -e "${BLUE}[7/7]${NC} Verificando frontend..."
if curl -s http://localhost/ | grep -q "Marshaall" 2>/dev/null; then
    echo -e "${GREEN}✓ Frontend accesible en http://localhost${NC}"
else
    echo -e "${RED}✗ Frontend NO accesible${NC}"
fi

# Resumen final
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  📊 RESUMEN                                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Obtener IP del host
HOST_IP=$(hostname -I | awk '{print $1}')
echo -e "${YELLOW}🌐 Acceso al Dashboard:${NC}"
echo -e "   URL: ${GREEN}http://localhost${NC} (o http://$HOST_IP)"
echo -e "   Usuario: ${GREEN}admin${NC}"
echo -e "   Contraseña: ${GREEN}admin1234${NC}"
echo ""

echo -e "${YELLOW}📝 Comandos útiles:${NC}"
echo -e "   # Generar eventos de prueba:"
echo -e "   ${GREEN}sudo ./scripts/generar_eventos_prueba.sh 100${NC}"
echo ""
echo -e "   # Ver eventos en tiempo real:"
echo -e "   ${GREEN}sudo tail -f /var/log/suricata/eve.json | grep alert${NC}"
echo ""
echo -e "   # Ver logs de ingesta:"
echo -e "   ${GREEN}docker logs -f marshaall-ingest --tail 50${NC}"
echo ""
echo -e "   # Reiniciar todos los servicios:"
echo -e "   ${GREEN}docker compose restart${NC}"
echo ""

echo -e "${YELLOW}🎯 Desde Kali Linux:${NC}"
echo -e "   # Copiar script a Kali:"
echo -e "   ${GREEN}scp scripts/kali_ataques.sh kali@<IP_KALI>:~/${NC}"
echo ""
echo -e "   # Ejecutar ataques desde Kali:"
echo -e "   ${GREEN}chmod +x kali_ataques.sh${NC}"
echo -e "   ${GREEN}./kali_ataques.sh $HOST_IP${NC}"
echo ""
