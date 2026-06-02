#!/usr/bin/env bash
# Truncate events + alert_status and verify
set -e

docker exec marshaall-mariadb bash -c \
  'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" marshaall -e "
     SET FOREIGN_KEY_CHECKS=0;
     TRUNCATE events;
     TRUNCATE alert_status;
     SET FOREIGN_KEY_CHECKS=1;
     SELECT COUNT(*) AS events_count FROM events;
     SELECT COUNT(*) AS alert_status_count FROM alert_status;
  "'

echo "=== BD truncada correctamente ==="
