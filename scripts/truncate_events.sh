#!/bin/bash
echo "=== Registros antes ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS events FROM events;
SELECT COUNT(*) AS alert_status FROM alert_status;
"

echo ""
echo "=== Limpiando tablas (FK disabled) ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE alert_status;
TRUNCATE TABLE events;
SET FOREIGN_KEY_CHECKS = 1;
"

echo ""
echo "=== Verificación ==="
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS events FROM events;
SELECT COUNT(*) AS alert_status FROM alert_status;
"
