# Guía de testing de emails — Marshaall

Esta guía cubre todas las formas de probar el sistema de emails de Marshaall:
email de prueba, alertas en tiempo real y reporte diario.

---

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Opción A — Servidor SMTP local con Mailpit (recomendado para desarrollo)](#2-opción-a--servidor-smtp-local-con-mailpit-recomendado-para-desarrollo)
3. [Opción B — Gmail como servidor SMTP](#3-opción-b--gmail-como-servidor-smtp)
4. [Opción C — Outlook / Office 365](#4-opción-c--outlook--office-365)
5. [Probar el email de prueba (endpoint `/api/test-email`)](#5-probar-el-email-de-prueba)
6. [Probar emails de alerta en tiempo real](#6-probar-emails-de-alerta-en-tiempo-real)
7. [Probar el reporte diario programado](#7-probar-el-reporte-diario-programado)
8. [Tests unitarios con mock de SMTP](#8-tests-unitarios-con-mock-de-smtp)
9. [Depuración y errores comunes](#9-depuración-y-errores-comunes)

---

## 1. Requisitos previos

- Docker y Docker Compose funcionando
- Marshaall levantado: `docker compose up -d`
- Archivo `.env` configurado (copiar de `.env.example`)
- Un usuario admin creado (por defecto: `admin` / `admin1234`)

---

## 2. Opción A — Servidor SMTP local con Mailpit (recomendado para desarrollo)

[Mailpit](https://github.com/axllent/mailpit) es un servidor SMTP falso que captura todos los emails
y los muestra en una interfaz web. **No envía nada a internet**, ideal para testing.

### Paso 1: Añadir Mailpit al `docker-compose.yml`

Agregar este servicio al archivo `docker-compose.yml`:

```yaml
  mailpit:
    image: axllent/mailpit:latest
    container_name: marshaall-mailpit
    restart: unless-stopped
    ports:
      - "8025:8025"   # Interfaz web
      - "1025:1025"   # SMTP
    networks:
      - backend_net
```

### Paso 2: Configurar `.env` para usar Mailpit

```dotenv
# --- SMTP (Email) --- Configuración para Mailpit local
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
SMTP_FROM=marshaall@localhost
SMTP_TLS=false

# --- Destinatarios ---
REPORT_TO=admin@test.com
ALERT_TO=admin@test.com
```

> **Nota:** Con Mailpit no se necesita usuario/contraseña ni TLS.

### Paso 3: Levantar los servicios

```bash
docker compose up -d
```

### Paso 4: Abrir la interfaz web de Mailpit

Abrir en el navegador: **http://localhost:8025**

Todos los emails enviados por Marshaall aparecerán aquí.

---

## 3. Opción B — Gmail como servidor SMTP

### Paso 1: Generar una "Contraseña de aplicación" en Gmail

1. Ir a [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Habilitar la verificación en 2 pasos si no está activa
3. Generar una contraseña de aplicación para "Correo" → "Otro" → "Marshaall"
4. Copiar la contraseña de 16 caracteres generada

### Paso 2: Configurar `.env`

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx    # Contraseña de aplicación (16 chars)
SMTP_FROM=tu-email@gmail.com
SMTP_TLS=true

REPORT_TO=destinatario@ejemplo.com
ALERT_TO=destinatario@ejemplo.com
```

### Paso 3: Reiniciar el backend

```bash
docker compose restart backend
```

---

## 4. Opción C — Outlook / Office 365

### Configurar `.env`

```dotenv
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=tu-email@tuempresa.com
SMTP_PASS=tu-contraseña
SMTP_FROM=tu-email@tuempresa.com
SMTP_TLS=true

REPORT_TO=destinatario@ejemplo.com
ALERT_TO=destinatario@ejemplo.com
```

---

## 5. Probar el email de prueba

El backend expone el endpoint `GET /api/test-email` (solo accesible para admin).

### Paso 1: Obtener token de autenticación

```bash
# Hacer login para obtener el token
curl -s -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}' | jq .
```

Respuesta esperada:
```json
{
  "token": "YWRtaW46YWRtaW46MTc...",
  "role": "admin",
  "username": "admin"
}
```

### Paso 2: Enviar email de prueba

```bash
# Reemplazar TOKEN con el valor obtenido arriba
curl -s http://localhost/api/test-email \
  -H "Authorization: Bearer TOKEN" | jq .
```

Respuestas posibles:

| Resultado | Respuesta |
|-----------|-----------|
| ✅ Éxito | `{"ok": true, "message": "Email de prueba enviado a admin@test.com"}` |
| ❌ SMTP no configurado | `{"error": "SMTP no configurado. Revise SMTP_HOST y SMTP_FROM en .env"}` |
| ❌ Sin destinatario | `{"error": "No hay destinatario configurado (REPORT_TO / ALERT_TO)"}` |
| ❌ Error de envío | `{"error": "Fallo al enviar email. Revise logs del backend y configuración SMTP."}` |

### Script rápido (todo en uno)

```bash
#!/bin/bash
# test_email.sh — Prueba rápida de email
TOKEN=$(curl -s -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}' | jq -r '.token')

echo "Token: $TOKEN"
echo "---"

curl -s http://localhost/api/test-email \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## 6. Probar emails de alerta en tiempo real

El endpoint `POST /api/notify-alert` es llamado internamente por el servicio `ingest`
cuando detecta una alerta de Suricata. Se puede invocar manualmente para testing.

### Requisito

La variable `INTERNAL_SECRET` debe estar configurada en `.env` y ser la misma que usa
el servicio ingest y el backend.

```dotenv
INTERNAL_SECRET=mi_secreto_de_prueba_123
```

### Enviar alerta de prueba

```bash
curl -s -X POST http://localhost/api/notify-alert \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: mi_secreto_de_prueba_123" \
  -d '{
    "severity": 1,
    "signature": "ET SCAN Nmap SYN Scan Detected",
    "src_ip": "192.168.1.100",
    "dest_ip": "10.0.0.5",
    "src_port": 54321,
    "dest_port": 22,
    "category": "Attempted Information Leak",
    "ts": "2026-02-28T12:00:00.000000+0100",
    "event_id": 99999
  }' | jq .
```

Respuestas posibles:

| Resultado | Respuesta |
|-----------|-----------|
| ✅ Enviado | `{"ok": true}` |
| ❌ No autorizado | `{"error": "No autorizado"}` (secreto incorrecto) |
| ❌ Sin destinatario | `{"ok": false, "reason": "no_recipient"}` |
| ⚠️ Deduplicado | `{"ok": false, "reason": "deduplicated"}` (misma alerta repetida en < 5 min) |
| ⚠️ Rate limit | `{"ok": false, "reason": "rate_limited"}` (> 5 emails/min) |

### Probar diferentes severidades

```bash
SECRET="mi_secreto_de_prueba_123"

# Severidad 1 (Alta - rojo)
curl -s -X POST http://localhost/api/notify-alert \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: $SECRET" \
  -d '{"severity":1,"signature":"ALTA: Posible intrusión detectada","src_ip":"10.0.0.1","dest_ip":"10.0.0.2","category":"Intrusion","ts":"2026-02-28T12:01:00","event_id":10001}' | jq .

# Severidad 2 (Media - amarillo)
curl -s -X POST http://localhost/api/notify-alert \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: $SECRET" \
  -d '{"severity":2,"signature":"MEDIA: Tráfico sospechoso","src_ip":"10.0.0.3","dest_ip":"10.0.0.4","category":"Suspicious","ts":"2026-02-28T12:02:00","event_id":10002}' | jq .

# Severidad 3 (Baja - verde)
curl -s -X POST http://localhost/api/notify-alert \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: $SECRET" \
  -d '{"severity":3,"signature":"BAJA: Consulta DNS inusual","src_ip":"10.0.0.5","dest_ip":"8.8.8.8","category":"DNS","ts":"2026-02-28T12:03:00","event_id":10003}' | jq .
```

> **Nota:** Si envías la misma combinación de `signature + src_ip + dest_ip` dentro de 5 minutos
> (configurable con `ALERT_DEDUP_WINDOW`), el email será deduplicado y no se reenviará.

---

## 7. Probar el reporte diario programado

El backend incluye un scheduler (APScheduler) que genera y envía un reporte PDF/HTML automáticamente.

### Ver si el scheduler está activo

```bash
docker logs marshaall-backend 2>&1 | grep -i scheduler
```

Salida esperada si está configurado:
```
Scheduler diario iniciado — reporte a las 08:00 (Europe/Madrid) para admin@test.com, rango=24h
```

Si no está configurado:
```
REPORT_TO no configurado — scheduler de reporte diario desactivado
```

### Forzar el envío del reporte manualmente

No hay un endpoint dedicado, pero puedes forzar la ejecución entrando al contenedor:

```bash
docker exec -it marshaall-backend python -c "
from app import generate_report_bytes, REPORT_TO, REPORT_RANGE
from emailer import send_report_email
from datetime import datetime

report_bytes, filename, mimetype = generate_report_bytes('24h', 'pdf')
print(f'Reporte generado: {filename} ({len(report_bytes)} bytes, {mimetype})')

ok = send_report_email('${REPORT_TO:-admin@test.com}', datetime.now().strftime('%Y-%m-%d'), report_bytes, filename, '24h')
print('Enviado!' if ok else 'Fallo al enviar')
"
```

### Descargar solo el reporte (sin enviar email)

```bash
# Obtener token
TOKEN=$(curl -s -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}' | jq -r '.token')

# Descargar PDF del reporte
curl -s http://localhost/api/report?range=24h \
  -H "Authorization: Bearer $TOKEN" \
  --output reporte_marshaall.pdf

echo "Reporte descargado: reporte_marshaall.pdf"
```

---

## 8. Tests unitarios con mock de SMTP

Para probar la lógica de emails sin necesidad de un servidor SMTP real,
puedes crear tests que mockean `smtplib.SMTP`.

### Crear archivo `backend/tests/test_emailer.py`

```python
"""
Tests del módulo emailer — ejecutar con: pytest tests/test_emailer.py -v
No requiere servidor SMTP real (usa mock).
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(autouse=True)
def smtp_env(monkeypatch):
    """Configura variables de entorno SMTP para los tests."""
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@test.com")
    monkeypatch.setenv("SMTP_PASS", "password123")
    monkeypatch.setenv("SMTP_FROM", "marshaall@test.com")
    monkeypatch.setenv("SMTP_TLS", "true")


# ------------------------------------------------------------------
# send_email
# ------------------------------------------------------------------

@patch("emailer.smtplib.SMTP")
def test_send_email_ok(mock_smtp_class):
    from emailer import send_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    result = send_email("dest@test.com", "Asunto Test", "<p>Hola</p>")

    assert result is True
    mock_smtp_class.assert_called_once_with("smtp.test.com", 587, timeout=30)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("test@test.com", "password123")
    mock_server.sendmail.assert_called_once()
    mock_server.quit.assert_called_once()


@patch("emailer.smtplib.SMTP")
def test_send_email_with_attachment(mock_smtp_class):
    from emailer import send_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    result = send_email(
        "dest@test.com", "Con adjunto", "<p>PDF</p>",
        attachment_bytes=b"%PDF-fake-content",
        attachment_name="reporte.pdf",
    )

    assert result is True
    # Verificar que el email contiene el adjunto
    call_args = mock_server.sendmail.call_args
    msg_str = call_args[0][2]
    assert "reporte.pdf" in msg_str


@patch("emailer.smtplib.SMTP")
def test_send_email_smtp_error(mock_smtp_class):
    from emailer import send_email
    mock_smtp_class.side_effect = Exception("Connection refused")

    result = send_email("dest@test.com", "Test", "<p>Hola</p>")

    assert result is False


def test_send_email_no_smtp_host(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    from emailer import send_email
    result = send_email("dest@test.com", "Test", "<p>Hola</p>")
    assert result is False


def test_send_email_no_recipient():
    from emailer import send_email
    result = send_email("", "Test", "<p>Hola</p>")
    assert result is False


# ------------------------------------------------------------------
# send_alert_email
# ------------------------------------------------------------------

@patch("emailer.smtplib.SMTP")
def test_send_alert_email_sev1(mock_smtp_class):
    from emailer import send_alert_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    alert = {
        "severity": 1,
        "signature": "ET SCAN Nmap SYN Scan",
        "src_ip": "192.168.1.100",
        "dest_ip": "10.0.0.5",
        "src_port": 54321,
        "dest_port": 22,
        "category": "Scan",
        "ts": "2026-02-28T12:00:00",
        "event_id": 99999,
    }

    result = send_alert_email("admin@test.com", alert)

    assert result is True
    call_args = mock_server.sendmail.call_args
    msg_str = call_args[0][2]
    assert "Sev.1" in msg_str
    assert "Nmap" in msg_str


# ------------------------------------------------------------------
# send_report_email
# ------------------------------------------------------------------

@patch("emailer.smtplib.SMTP")
def test_send_report_email(mock_smtp_class):
    from emailer import send_report_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    result = send_report_email(
        "admin@test.com", "2026-02-28",
        b"%PDF-fake", "reporte.pdf", "24h",
    )

    assert result is True
    call_args = mock_server.sendmail.call_args
    msg_str = call_args[0][2]
    assert "Reporte" in msg_str or "REPORTE" in msg_str


# ------------------------------------------------------------------
# is_smtp_configured
# ------------------------------------------------------------------

def test_is_smtp_configured_yes():
    from emailer import is_smtp_configured
    assert is_smtp_configured() is True


def test_is_smtp_configured_no(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    from emailer import is_smtp_configured
    assert is_smtp_configured() is False
```

### Ejecutar los tests

```bash
# Desde la raíz del proyecto
docker exec -it marshaall-backend pytest tests/test_emailer.py -v

# O localmente si tienes Python instalado
cd backend
pip install -r requirements.txt
pytest tests/test_emailer.py -v
```

---

## 9. Depuración y errores comunes

### Ver logs del backend en tiempo real

```bash
docker logs -f marshaall-backend 2>&1 | grep -i "email\|smtp\|scheduler"
```

### Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `SMTP no configurado` | `SMTP_HOST` o `SMTP_FROM` vacíos en `.env` | Rellenar ambas variables y reiniciar: `docker compose restart backend` |
| `Connection refused` | El servidor SMTP no es accesible | Verificar host/puerto. Con Mailpit, asegurar que el contenedor está levantado |
| `Authentication failed` | Credenciales SMTP incorrectas | Con Gmail, usar contraseña de aplicación (no la contraseña normal) |
| `STARTTLS extension not supported` | Se usa `SMTP_TLS=true` con un servidor que no soporta TLS | Cambiar a `SMTP_TLS=false` (ej: Mailpit no requiere TLS) |
| `No hay destinatario` | `REPORT_TO` y `ALERT_TO` vacíos | Configurar al menos uno en `.env` |
| `rate_limited` | Más de 5 alertas/minuto | Esperar 1 minuto o aumentar `ALERT_MAX_EMAIL_PER_MIN` |
| `deduplicated` | Misma alerta (firma+IP) repetida en < 5 min | Esperar `ALERT_DEDUP_WINDOW` segundos o cambiar los campos de la alerta |

### Verificar conectividad SMTP desde el contenedor

```bash
# Probar conexión TCP al servidor SMTP
docker exec -it marshaall-backend python -c "
import socket
host, port = 'mailpit', 1025  # Cambiar según tu configuración
try:
    s = socket.create_connection((host, port), timeout=5)
    print(f'✅ Conexión a {host}:{port} exitosa')
    s.close()
except Exception as e:
    print(f'❌ No se puede conectar a {host}:{port}: {e}')
"
```

### Verificar las variables de entorno cargadas

```bash
docker exec -it marshaall-backend python -c "
from emailer import get_smtp_config, is_smtp_configured
import os
cfg = get_smtp_config()
print('=== Configuración SMTP ===')
for k, v in cfg.items():
    if k == 'password':
        v = '****' if v else '(vacío)'
    print(f'  {k}: {v}')
print(f'  SMTP configurado: {is_smtp_configured()}')
print(f'  REPORT_TO: {os.getenv(\"REPORT_TO\", \"(vacío)\")}')
print(f'  ALERT_TO:  {os.getenv(\"ALERT_TO\", \"(vacío)\")}')
"
```

---

## Resumen rápido

| Qué probar | Cómo |
|-------------|------|
| Email de prueba | `GET /api/test-email` (requiere token admin) |
| Alerta en tiempo real | `POST /api/notify-alert` (requiere `X-Internal-Secret`) |
| Reporte diario | Automático vía scheduler, o forzar desde el contenedor |
| Tests unitarios | `pytest tests/test_emailer.py -v` |
| Ver emails capturados | Mailpit en `http://localhost:8025` |
