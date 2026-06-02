#!/bin/bash
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SET FOREIGN_KEY_CHECKS=0;
TRUNCATE TABLE alert_status;
TRUNCATE TABLE events;
SET FOREIGN_KEY_CHECKS=1;
SELECT 'events' AS tabla, COUNT(*) AS filas FROM events
UNION ALL
SELECT 'alert_status', COUNT(*) FROM alert_status;
"
