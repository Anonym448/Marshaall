#!/bin/bash
# ============================================================
# Marshaall — Suricata Startup Script (WSL2)
# ============================================================
# Interfaces: lo (Docker/IPv6 loopback) + eth0 (red externa)
# -k none: sin checksum validation (necesario en WSL2/loopback)
# Para arranque automatico: systemctl start suricata
# ============================================================

CONF="/etc/suricata/suricata.yaml"
PIDFILE="/run/suricata.pid"
RULESRC="/home/user/marshaall/suricata/local.rules"
RULEDST="/var/lib/suricata/rules/local.rules"

echo "[Marshaall] Sincronizando reglas..."
cp "$RULESRC" "$RULEDST" || { echo "ERROR: Ejecuta como root (sudo)"; exit 1; }

echo "[Marshaall] Deteniendo Suricata existente..."
pkill suricata 2>/dev/null; sleep 2; pkill -9 suricata 2>/dev/null; rm -f "$PIDFILE"

echo "[Marshaall] Arrancando Suricata (lo + eth0, -k none)..."
suricata --pcap=lo --pcap=eth0 -c "$CONF" -D --pidfile "$PIDFILE" -k none 2>&1
sleep 6

if ps aux | grep -q "[s]uricata"; then
    echo "[Marshaall] Suricata ACTIVO"
    grep "rules successfully loaded" /var/log/suricata/suricata.log | tail -1
else
    echo "[Marshaall] ERROR: Suricata no arranco"
    tail -10 /var/log/suricata/suricata.log; exit 1
fi
