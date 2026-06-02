#!/usr/bin/env bash
# =============================================================
# Marshaall SIEM — Script de verificación y gestión de Suricata
# Uso: bash check_suricata.sh [status|install|start|stop|update-rules|test]
# =============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $*"; }
log_err()  { echo -e "${RED}[✗]${NC} $*"; }
log_info() { echo -e "${BLUE}[i]${NC} $*"; }

SURICATA_LOG_DIR="/var/log/suricata"
EVE_JSON="${SURICATA_LOG_DIR}/eve.json"
SURICATA_CONF="/etc/suricata/suricata.yaml"

check_installed() {
    if command -v suricata &>/dev/null; then
        local ver
        ver=$(suricata --build-info 2>&1 | grep "^Version" | awk '{print $2}')
        log_ok "Suricata instalado — versión: ${ver:-desconocida}"
        return 0
    else
        log_err "Suricata NO está instalado en este sistema."
        log_info "Instálalo con: sudo apt install suricata   (Ubuntu/Debian)"
        log_info "              sudo yum install suricata    (CentOS/RHEL)"
        return 1
    fi
}

check_service() {
    log_info "Estado del servicio Suricata..."
    if systemctl is-active --quiet suricata 2>/dev/null; then
        log_ok "Servicio 'suricata' ACTIVO (systemd)"
    elif pgrep -x suricata &>/dev/null; then
        log_ok "Proceso suricata EN EJECUCIÓN (PID: $(pgrep -x suricata | head -1))"
    else
        log_warn "Suricata NO está en ejecución."
        log_info "Inicia con: sudo systemctl start suricata"
        log_info "  o bien:   sudo systemctl enable --now suricata"
    fi
}

check_eve_log() {
    log_info "Verificando log EVE JSON..."
    if [[ -f "$EVE_JSON" ]]; then
        local size
        size=$(du -sh "$EVE_JSON" 2>/dev/null | awk '{print $1}')
        local lines
        lines=$(wc -l < "$EVE_JSON" 2>/dev/null || echo 0)
        log_ok "Fichero EVE JSON existe: ${EVE_JSON}"
        log_info "  Tamaño: ${size} | Eventos: ${lines}"
        # Mostrar último evento
        local last
        last=$(tail -1 "$EVE_JSON" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20 || tail -1 "$EVE_JSON" 2>/dev/null | head -c 300)
        if [[ -n "$last" ]]; then
            echo ""
            log_info "Último evento:"
            echo "$last"
            echo ""
        fi
    else
        log_warn "Fichero EVE JSON NO existe: ${EVE_JSON}"
        log_info "Suricata aún no ha capturado eventos, o no está en ejecución."
        log_info "Asegúrate de que el log dir existe: sudo mkdir -p ${SURICATA_LOG_DIR}"
    fi
}

check_config() {
    log_info "Verificando configuración de Suricata..."
    if [[ -f "$SURICATA_CONF" ]]; then
        log_ok "Fichero de configuración encontrado: ${SURICATA_CONF}"
        # Test de sintaxis
        if suricata -T -c "$SURICATA_CONF" --no-random 2>&1 | grep -q "Configuration provided was successfully loaded"; then
            log_ok "Sintaxis de configuración VÁLIDA"
        else
            log_warn "Test de configuración:"
            suricata -T -c "$SURICATA_CONF" --no-random 2>&1 | tail -5
        fi
    else
        log_warn "No se encontró configuración en ${SURICATA_CONF}"
        log_info "Copia la config de Marshaall: sudo cp suricata/suricata.yaml /etc/suricata/suricata.yaml"
    fi
}

check_rules() {
    log_info "Verificando reglas de detección..."
    local rules_dir="/var/lib/suricata/rules"
    if [[ -d "$rules_dir" ]]; then
        local count
        count=$(find "$rules_dir" -name "*.rules" 2>/dev/null | xargs grep -h "^alert" 2>/dev/null | wc -l || echo 0)
        log_ok "Directorio de reglas: ${rules_dir}"
        log_info "  Reglas cargadas (aprox): ${count}"
    else
        log_warn "Directorio de reglas no encontrado: ${rules_dir}"
        log_info "Actualiza las reglas con: sudo suricata-update"
    fi
}

install_suricata() {
    log_info "Instalando Suricata..."
    if ! command -v add-apt-repository &>/dev/null; then
        sudo apt-get install -y software-properties-common
    fi
    sudo add-apt-repository -y ppa:oisf/suricata-stable
    sudo apt-get update -q
    sudo apt-get install -y suricata
    log_ok "Suricata instalado correctamente."
    update_rules
    install_config
}

install_config() {
    log_info "Instalando configuración Marshaall en /etc/suricata/suricata.yaml..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "${SCRIPT_DIR}/suricata.yaml" ]]; then
        sudo cp "${SCRIPT_DIR}/suricata.yaml" /etc/suricata/suricata.yaml
        log_ok "Configuración instalada."
        log_warn "RECUERDA: edita /etc/suricata/suricata.yaml y ajusta la interfaz de red (af-packet -> interface)."
        log_info "Para ver tus interfaces: ip link show"
    else
        log_err "No se encontró suricata/suricata.yaml en el repositorio."
    fi
}

update_rules() {
    log_info "Actualizando reglas (suricata-update)..."
    if command -v suricata-update &>/dev/null; then
        sudo suricata-update
        log_ok "Reglas actualizadas."
    else
        log_warn "suricata-update no está instalado."
        sudo apt-get install -y python3-suricata-update 2>/dev/null || true
        sudo pip3 install suricata-update 2>/dev/null || true
        sudo suricata-update || log_err "No se pudo actualizar las reglas."
    fi
}

start_suricata() {
    log_info "Iniciando Suricata..."
    sudo systemctl enable suricata
    sudo systemctl start suricata
    sleep 2
    check_service
}

stop_suricata() {
    log_info "Deteniendo Suricata..."
    sudo systemctl stop suricata
    log_ok "Suricata detenido."
}

test_suricata() {
    log_info "Generando tráfico de prueba para verificar la detección..."
    # Test con una petición HTTP sencilla que Suricata detectará
    curl -sS http://testmynids.org/uid/index.html -o /dev/null 2>/dev/null || \
        wget -q http://testmynids.org/uid/index.html -O /dev/null 2>/dev/null || \
        log_warn "No se pudo hacer la petición de prueba (sin acceso a internet)"
    sleep 2
    log_info "Verificando si se generaron eventos..."
    check_eve_log
}

full_status() {
    echo ""
    echo "======================================================="
    echo "  Marshaall SIEM — Estado de Suricata"
    echo "======================================================="
    echo ""
    check_installed || exit 1
    echo ""
    check_service
    echo ""
    check_config
    echo ""
    check_rules
    echo ""
    check_eve_log
    echo ""
    echo "======================================================="
    echo "  Integración con docker-compose de Marshaall:"
    echo "  El servicio 'ingest' lee: /var/log/suricata/eve.json"
    echo "  Asegúrate de que Suricata escribe en esa ruta."
    echo "======================================================="
    echo ""
}

case "${1:-status}" in
    status)        full_status ;;
    install)       install_suricata ;;
    install-config) install_config ;;
    start)         start_suricata ;;
    stop)          stop_suricata ;;
    update-rules)  update_rules ;;
    test)          test_suricata ;;
    *)
        echo "Uso: bash check_suricata.sh [status|install|install-config|start|stop|update-rules|test]"
        echo ""
        echo "  status         — Muestra el estado completo de Suricata"
        echo "  install        — Instala Suricata y configura para Marshaall"
        echo "  install-config — Solo instala el fichero de configuración"
        echo "  start          — Inicia el servicio Suricata"
        echo "  stop           — Detiene el servicio Suricata"
        echo "  update-rules   — Actualiza las reglas de detección"
        echo "  test           — Genera tráfico de prueba y verifica detección"
        exit 1
        ;;
esac
