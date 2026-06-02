#!/bin/bash
docker exec marshaall-mariadb mariadb -u marshaall -p'mariadb_sudo$628' marshaall -e "
SELECT COUNT(*) AS total_events FROM events;
SELECT event_type, COUNT(*) AS cnt FROM events GROUP BY event_type ORDER BY cnt DESC;
SELECT id, event_type, signature, severity, src_ip, dest_ip, ts
FROM events WHERE event_type='alert' ORDER BY id DESC LIMIT 10;
"
