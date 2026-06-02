#!/usr/bin/env bash
# Query last 10 events from DB
docker exec marshaall-mariadb bash -c \
  'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" marshaall -e "
     SELECT id, ts, event_type, src_ip, dest_ip, signature, severity
     FROM events ORDER BY id DESC LIMIT 10;
  "'
echo "---"
docker exec marshaall-mariadb bash -c \
  'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" marshaall -e "
     SELECT COUNT(*) AS total_events,
            SUM(event_type=\"alert\") AS alerts
     FROM events;
  "'
