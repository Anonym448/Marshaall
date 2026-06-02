"""
marshaall-backend: Módulo reutilizable de envío de emails por SMTP.
Lee toda la configuración de variables de entorno.
"""

import os
import base64
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

log = logging.getLogger("backend")

_LOGO_BYTES = None

def _load_logo_bytes():
    global _LOGO_BYTES
    if _LOGO_BYTES is not None:
        return _LOGO_BYTES
    for path in ["/usr/share/nginx/html/imagenes/logotipo.png",
                 os.path.join(os.path.dirname(__file__), "..", "frontend", "imagenes", "logotipo.png")]:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    _LOGO_BYTES = f.read()
                log.info("Logo cargado para emails desde %s (%d bytes)", path, len(_LOGO_BYTES))
                return _LOGO_BYTES
        except Exception as e:
            log.warning("No se pudo cargar logo desde %s: %s", path, e)
    return None


# ---------------------------------------------------------------------------
# Configuración SMTP (leída de variables de entorno)
# ---------------------------------------------------------------------------

def get_smtp_config():
    """Devuelve un dict con la configuración SMTP actual."""
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "from_addr": os.getenv("SMTP_FROM", ""),
        "use_tls": os.getenv("SMTP_TLS", "true").lower() in ("true", "1", "yes"),
    }


def is_smtp_configured():
    """Devuelve True si hay al menos host y from configurados."""
    cfg = get_smtp_config()
    return bool(cfg["host"] and cfg["from_addr"])


# ---------------------------------------------------------------------------
# Función genérica de envío
# ---------------------------------------------------------------------------

def send_email(to, subject, body_html, attachment_bytes=None, attachment_name=None):
    """
    Envía un email por SMTP.

    Args:
        to: dirección destinatario.
        subject: asunto del email.
        body_html: cuerpo en HTML.
        attachment_bytes: bytes opcionales del adjunto.
        attachment_name: nombre de fichero del adjunto.

    Returns:
        True si se envió correctamente, False en caso contrario.
    """
    cfg = get_smtp_config()
    if not cfg["host"] or not cfg["from_addr"]:
        log.warning("SMTP no configurado (SMTP_HOST / SMTP_FROM vacíos), email omitido")
        return False
    if not to:
        log.warning("Destinatario vacío, email omitido")
        return False

    msg = MIMEMultipart("mixed")
    msg["From"] = cfg["from_addr"]
    msg["To"] = to
    msg["Subject"] = subject
    msg_related = MIMEMultipart("related")
    msg_related.attach(MIMEText(body_html, "html", "utf-8"))
    logo_data = _load_logo_bytes()
    if logo_data:
        logo_part = MIMEImage(logo_data, _subtype="png")
        logo_part.add_header("Content-ID", "<marshaall_logo>")
        logo_part.add_header("Content-Disposition", "inline", filename="logotipo.png")
        msg_related.attach(logo_part)
    msg.attach(msg_related)

    if attachment_bytes and attachment_name:
        part = MIMEApplication(attachment_bytes, Name=attachment_name)
        part.add_header("Content-Disposition", "attachment", filename=attachment_name)
        msg.attach(part)

    try:
        if cfg["use_tls"]:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
            server.ehlo()

        if cfg["user"].strip() and cfg["password"].strip():
            server.login(cfg["user"], cfg["password"])

        server.sendmail(cfg["from_addr"], [to], msg.as_string())
        server.quit()
        log.info("Email enviado a %s — asunto: %s", to, subject)
        return True
    except Exception as e:
        log.error("Error enviando email a %s: %s", to, e)
        return False


# ---------------------------------------------------------------------------
# Helpers especializados
# ---------------------------------------------------------------------------

def send_report_email(to, report_date, attachment_bytes, attachment_name, report_range="24h"):
    """Envía el reporte diario de Marshaall."""
    subject = "Marshaall — Reporte Diario ({})".format(report_date)
    body = """
    <div style="font-family:'Inter',system-ui,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#0f1b2d;padding:24px 32px;border-radius:12px 12px 0 0;border:1px solid rgba(59,130,246,0.12);border-bottom:none;">
        <div style="display:flex;align-items:center;gap:16px;">
          <div style="display:inline-flex;align-items:center;justify-content:center;border-radius:12px;padding:6px 14px;flex-shrink:0;">
            <img src="cid:marshaall_logo" alt="Marshaall" style="height:48px;width:auto;" />
          </div>
          <div>
            <h1 style="color:#fff;margin:0;font-size:22px;letter-spacing:1.5px;">MARSHAALL</h1>
            <p style="color:#60a5fa;margin:4px 0 0;font-size:13px;letter-spacing:2px;">REPORTE DE SEGURIDAD</p>
          </div>
        </div>
      </div>
      <div style="background:#fff;padding:24px 32px;border:1px solid rgba(59,130,246,0.1);border-top:none;">
        <p style="color:#374151;font-size:14px;line-height:1.5;">
          Adjunto el reporte de seguridad para el rango <strong>{range}</strong>,
          generado el <strong>{date}</strong>.
        </p>
        <p style="color:#64748b;font-size:13px;margin-top:16px;">
          Este email es generado automáticamente por Marshaall Cybersecurity Software.
        </p>
      </div>
      <div style="background:#eef1f6;padding:16px 32px;border-radius:0 0 12px 12px;border:1px solid rgba(59,130,246,0.1);border-top:none;">
        <p style="color:#94a3b8;font-size:11px;margin:0;">Marshaall — Plataforma de ciberseguridad para PYMEs</p>
      </div>
    </div>
    """.format(range=report_range, date=report_date)

    return send_email(to, subject, body, attachment_bytes, attachment_name)


CATEGORY_ES = {
    "A Network Trojan was detected": "Troyano de red detectado",
    "Attempted Information Leak": "Intento de fuga de información",
    "Misc activity": "Actividad diversa",
    "Misc Attack": "Ataque diverso",
    "Potentially Bad Traffic": "Tráfico potencialmente malicioso",
    "Web Application Attack": "Ataque a aplicación web",
    "Attempted Denial of Service": "Intento de denegación de servicio",
    "Detection of a Network Scan": "Escaneo de red detectado",
    "Attempted User Privilege Gain": "Intento de escalada de privilegios",
    "Attempted Administrator Privilege Gain": "Intento de acceso como administrador",
    "Successful Administrator Privilege Gain": "Acceso de administrador logrado",
    "Executable Code was Detected": "Código ejecutable detectado",
    "A suspicious filename was detected": "Nombre de archivo sospechoso",
    "Not Suspicious Traffic": "Tráfico no sospechoso",
    "Generic Protocol Command Decode": "Decodificación genérica de protocolo",
    "Policy Violation": "Violación de política",
    "Malware Command and Control Activity": "Actividad C2 de malware",
    "access to a potentially vulnerable web application": "Acceso a aplicación web vulnerable",
}

def translate_category(cat):
    if not cat:
        return ""
    if cat in CATEGORY_ES:
        return CATEGORY_ES[cat]
    for en, es in CATEGORY_ES.items():
        if cat.lower().startswith(en.lower()[:20]):
            return es
    return cat


def send_alert_email(to, alert_data):
    """Envía una notificación de alerta en tiempo real."""
    severity = alert_data.get("severity")
    sev_map = {1: ("Alta", "#ef4444"), 2: ("Media", "#f59e0b"), 3: ("Baja", "#eab308")}
    sev_label, sev_color = sev_map.get(severity, ("Info", "#6b7280"))

    signature = alert_data.get("signature", "Sin firma")
    src_ip = alert_data.get("src_ip", "—")
    dest_ip = alert_data.get("dest_ip", "—")
    src_port = alert_data.get("src_port", "")
    dest_port = alert_data.get("dest_port", "")
    category = translate_category(alert_data.get("category", ""))
    ts = alert_data.get("ts", "")
    event_id = alert_data.get("event_id", "")

    subject = "Marshaall ⚠ Alerta Sev.{} — {}".format(severity or "?", signature[:60])

    body = """
    <div style="font-family:'Inter',system-ui,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#0f1b2d;padding:24px 32px;border-radius:12px 12px 0 0;border:1px solid rgba(59,130,246,0.12);border-bottom:none;">
        <div style="display:flex;align-items:center;gap:16px;">
          <div style="display:inline-flex;align-items:center;justify-content:center;border-radius:12px;padding:6px 14px;flex-shrink:0;">
            <img src="cid:marshaall_logo" alt="Marshaall" style="height:48px;width:auto;" />
          </div>
          <div>
            <h1 style="color:#fff;margin:0;font-size:22px;letter-spacing:1.5px;">MARSHAALL</h1>
            <p style="color:#60a5fa;margin:4px 0 0;font-size:13px;letter-spacing:2px;">ALERTA EN TIEMPO REAL</p>
          </div>
        </div>
      </div>
      <div style="background:#fff;padding:24px 32px;border:1px solid rgba(59,130,246,0.1);border-top:none;">
        <div style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:13px;font-weight:600;color:#fff;background:{sev_color};margin-bottom:12px;">
          Severidad {severity} — {sev_label}
        </div>
        <table style="width:100%;font-size:14px;color:#374151;border-collapse:collapse;">
          <tr><td style="padding:6px 0;font-weight:600;width:130px;">ID Evento</td><td>{event_id}</td></tr>
          <tr><td style="padding:6px 0;font-weight:600;">Firma</td><td>{signature}</td></tr>
          <tr><td style="padding:6px 0;font-weight:600;">Categoría</td><td>{category}</td></tr>
          <tr><td style="padding:6px 0;font-weight:600;">Origen</td><td>{src_ip}{src_port_str}</td></tr>
          <tr><td style="padding:6px 0;font-weight:600;">Destino</td><td>{dest_ip}{dest_port_str}</td></tr>
          <tr><td style="padding:6px 0;font-weight:600;">Fecha</td><td>{ts}</td></tr>
        </table>
      </div>
      <div style="background:#eef1f6;padding:16px 32px;border-radius:0 0 12px 12px;border:1px solid rgba(59,130,246,0.1);border-top:none;">
        <p style="color:#94a3b8;font-size:11px;margin:0;">Marshaall — Alerta automática. Revisar en el panel de control.</p>
      </div>
    </div>
    """.format(
        sev_color=sev_color,
        severity=severity or "?",
        sev_label=sev_label,
        event_id=event_id,
        signature=signature,
        category=category or "—",
        src_ip=src_ip,
        src_port_str=":{}".format(src_port) if src_port else "",
        dest_ip=dest_ip,
        dest_port_str=":{}".format(dest_port) if dest_port else "",
        ts=ts,
    )

    return send_email(to, subject, body)
