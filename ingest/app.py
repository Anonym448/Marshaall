"""
marshaall-ingest: Servicio de ingesta de EVE JSON (Suricata).
"""

import os
import json
import time
import logging
import pymysql
import requests
import pytz

LOCAL_TZ = pytz.timezone(os.getenv("TZ", "Europe/Madrid"))
from dateutil import parser as dtparser

DB_HOST     = os.getenv("DB_HOST", "mariadb")
DB_NAME     = os.getenv("DB_NAME", "marshaall")
DB_USER     = os.getenv("DB_USER", "marshaall")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

EVE_PATH    = os.getenv("EVE_PATH", "/data/eve.json")
STATE_PATH  = os.getenv("STATE_PATH", "/state/offset.txt")
BATCH_SIZE  = int(os.getenv("BATCH_SIZE", "200"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "0.5"))

BACKEND_URL     = os.getenv("BACKEND_URL", "http://backend:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")

logging.basicConfig(
    level=logging.INFO,
    format="[ingest] %(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ingest")


def load_offset():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            s = f.read().strip()
            return int(s) if s else 0
    except Exception:
        return 0


def save_offset(n):
    os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(str(int(n)))
    os.replace(tmp, STATE_PATH)


def connect_db():
    for attempt in range(30):
        try:
            conn = pymysql.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                database=DB_NAME, charset="utf8mb4", autocommit=True,
            )
            log.info("Conectado a MariaDB")
            return conn
        except Exception as e:
            log.warning("BD no disponible (intento %d): %s", attempt + 1, e)
            time.sleep(2)
    raise RuntimeError("No se pudo conectar a MariaDB tras 30 intentos")


def ensure_connection(conn):
    try:
        conn.ping(reconnect=True)
        return conn
    except Exception:
        log.warning("Conexion perdida, reconectando...")
        return connect_db()


def extract_event_fields(evt, raw_line):
    ts_raw = evt.get("timestamp")
    ts = None
    if ts_raw:
        try:
            dt = dtparser.isoparse(ts_raw)
            # Convertir a hora local para almacenar en DATETIME (sin TZ)
            if dt.tzinfo is not None:
                dt = dt.astimezone(LOCAL_TZ)
            ts = dt.replace(tzinfo=None)  # Quitar tzinfo para DATETIME
        except Exception:
            ts = None


    event_type = evt.get("event_type")
    src_ip     = evt.get("src_ip")
    dest_ip    = evt.get("dest_ip")
    proto      = evt.get("proto")
    src_port   = evt.get("src_port")
    dest_port  = evt.get("dest_port")
    flow_id    = evt.get("flow_id")

    signature = None
    severity  = None
    category  = None

    if event_type == "alert":
        alert = evt.get("alert") or {}
        signature = alert.get("signature")
        severity  = alert.get("severity")
        category  = alert.get("category")

    return {
        "ts": ts, "event_type": event_type,
        "src_ip": src_ip, "dest_ip": dest_ip, "proto": proto,
        "signature": signature, "severity": severity,
        "flow_id": flow_id, "src_port": src_port,
        "dest_port": dest_port, "category": category,
        "raw_json": raw_line,
    }


INSERT_SQL = (
    "INSERT INTO events"
    " (ts, event_type, src_ip, dest_ip, proto, signature, severity,"
    " flow_id, src_port, dest_port, category, raw_json)"
    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
)

DEDUP_SQL = "SELECT 1 FROM events WHERE flow_id = %s AND ts = %s LIMIT 1"

ALERT_STATUS_SQL = "INSERT IGNORE INTO alert_status (event_id, status) VALUES (%s, 'nueva')"


def is_duplicate(cur, fields):
    if fields["flow_id"] is None or fields["ts"] is None:
        return False
    cur.execute(DEDUP_SQL, (fields["flow_id"], fields["ts"]))
    return cur.fetchone() is not None


def insert_event(cur, fields):
    cur.execute(INSERT_SQL, (
        fields["ts"], fields["event_type"], fields["src_ip"], fields["dest_ip"],
        fields["proto"], fields["signature"], fields["severity"],
        fields["flow_id"], fields["src_port"], fields["dest_port"],
        fields["category"], fields["raw_json"],
    ))
    return cur.lastrowid


def notify_alert(fields, event_id):
    """Notifica al backend de una nueva alerta para envío de email en tiempo real."""
    if not INTERNAL_SECRET:
        return
    try:
        resp = requests.post(
            "{}/api/notify-alert".format(BACKEND_URL),
            json={
                "event_id": event_id,
                "signature": fields.get("signature"),
                "severity": fields.get("severity"),
                "src_ip": fields.get("src_ip"),
                "dest_ip": fields.get("dest_ip"),
                "src_port": fields.get("src_port"),
                "dest_port": fields.get("dest_port"),
                "category": fields.get("category"),
                "ts": str(fields.get("ts", "")),
            },
            headers={"X-Internal-Secret": INTERNAL_SECRET},
            timeout=5,
        )
        if resp.status_code not in (200, 429):
            log.warning("notify-alert respondió %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.warning("No se pudo notificar alerta al backend: %s", e)


def wait_for_file(path):
    while not os.path.exists(path):
        log.info("Esperando fichero %s ...", path)
        time.sleep(5)
    log.info("Fichero detectado: %s", path)


def main():
    wait_for_file(EVE_PATH)
    conn = connect_db()
    offset = load_offset()
    log.info("Offset inicial: %d", offset)

    inserted_total = 0
    dupes_total = 0
    errors_total = 0

    while True:
        conn = ensure_connection(conn)
        try:
            size = os.path.getsize(EVE_PATH)
        except OSError:
            log.warning("No se puede leer tamano de %s", EVE_PATH)
            time.sleep(5)
            continue

        if offset > size:
            log.info("Truncate detectado (offset %d > size %d). Reset a 0.", offset, size)
            offset = 0
            save_offset(offset)

        batch_count = 0
        try:
            with open(EVE_PATH, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(offset)
                with conn.cursor() as cur:
                    while batch_count < BATCH_SIZE:
                        line = f.readline()
                        if not line:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            evt = json.loads(line)

                            # Solo ingestar alertas y stats (para heartbeat)
                            if evt.get("event_type") not in ("alert"):
                                continue

                            fields = extract_event_fields(evt, line)

                            if is_duplicate(cur, fields):
                                dupes_total += 1
                                continue
                            event_id = insert_event(cur, fields)
                            inserted_total += 1
                            batch_count += 1
                            if fields["event_type"] == "alert" and event_id:
                                try:
                                    cur.execute(ALERT_STATUS_SQL, (event_id,))
                                except Exception:
                                    pass
                                # Notificar al backend para email en tiempo real
                                notify_alert(fields, event_id)
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            errors_total += 1
                            log.error("Error procesando evento: %s", e)
                            time.sleep(0.1)
                offset = f.tell()
                save_offset(offset)
        except Exception as e:
            log.error("Error leyendo fichero: %s", e)
            time.sleep(5)
            continue

        if batch_count > 0:
            log.info("Batch: +%d insertados (total: %d, dupes: %d, errores: %d)",
                     batch_count, inserted_total, dupes_total, errors_total)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
