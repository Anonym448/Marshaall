"""
marshaall-backend: API REST principal.
Flask + PyMySQL, autenticacion HMAC, roles (admin/analista/viewer).
"""

import os
import io
import base64
import hmac
import time
import logging
import functools
import traceback
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pymysql
import pytz
import jwt
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, g, Response
from werkzeug.security import check_password_hash, generate_password_hash

DB_HOST     = os.getenv("DB_HOST", "mariadb")
DB_NAME     = os.getenv("DB_NAME", "marshaall")
DB_USER     = os.getenv("DB_USER", "marshaall")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

API_SECRET         = os.getenv("API_SECRET", "CAMBIAME_EN_.ENV")
TOKEN_TTL_SECONDS  = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

# Email / Scheduler / Alert notification config
SMTP_HOST      = os.getenv("SMTP_HOST", "")
REPORT_TO      = os.getenv("REPORT_TO", "")
ALERT_TO       = os.getenv("ALERT_TO", "") or os.getenv("REPORT_TO", "")
REPORT_TIME    = os.getenv("REPORT_TIME", "06:00")
REPORT_TZ      = os.getenv("REPORT_TZ", "Europe/Madrid")
REPORT_RANGE   = os.getenv("REPORT_RANGE", "24h")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")
ALERT_DEDUP_WINDOW   = int(os.getenv("ALERT_DEDUP_WINDOW", "300"))   # segundos
ALERT_MAX_PER_MIN    = int(os.getenv("ALERT_MAX_EMAIL_PER_MIN", "5"))

# Centralized Logging Setup
log_dir = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
log_file = os.path.join(log_dir, "app.log")

file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

log = logging.getLogger("marshaall")
log.setLevel(logging.INFO)
log.addHandler(file_handler)
log.addHandler(logging.StreamHandler())

app = Flask(__name__)

@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def log_request(response):
    if request.path.startswith("/api"):
        duration = time.time() - g.get('start_time', time.time())
        user = g.get('user', 'anonymous')
        log.info(f"{request.method} {request.path} {response.status_code} {duration:.4f}s - User: {user}")
    return response


def db():
    if "db" not in g or not g.db.open:
        g.db = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, charset="utf8mb4", autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
    return g.db


@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn and conn.open:
        conn.close()


def get_conn():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4", autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def make_token(username, role):
    payload = {
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(seconds=TOKEN_TTL_SECONDS)
    }
    return jwt.encode(payload, API_SECRET, algorithm="HS256")


def verify_token(token):
    try:
        payload = jwt.decode(token, API_SECRET, algorithms=["HS256"])
        return payload.get("username"), payload.get("role")
    except jwt.ExpiredSignatureError:
        return None, None
    except jwt.InvalidTokenError:
        return None, None
    except Exception:
        return None, None


def require_auth():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.replace("Bearer ", "", 1).strip()
        return verify_token(token)
    # Fallback: token en query string (para descargas desde navegador)
    token_qs = request.args.get("token", "").strip()
    if token_qs:
        return verify_token(token_qs)
    return None, None


def auth_required(min_role=None):
    roles_order = {"viewer": 0, "analista": 1, "admin": 2}
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            username, role = require_auth()
            if not username:
                return jsonify({"error": "No autorizado"}), 401
            if min_role and roles_order.get(role, 0) < roles_order.get(min_role, 0):
                return jsonify({"error": "Permisos insuficientes"}), 403
            g.user = username
            g.role = role
            return fn(*a, **kw)
        return wrapper
    return decorator


def parse_int(val, default, lo, hi):
    try:
        v = int(val)
        return max(lo, min(v, hi))
    except (TypeError, ValueError):
        return default


def paginated_args():
    page = parse_int(request.args.get("page"), 1, 1, 10000)
    per_page = parse_int(request.args.get("per_page"), 25, 1, 200)
    return page, per_page


def is_critical_alert(signature, category):
    """Detecta si una alerta es de urgencia crítica (Ransomware, C2, etc)."""
    text = f"{signature} {category}".lower()
    keywords = ["ransomware", "crypto", "wannacry", "trojan", "c2", "cobalt strike", "meterpreter"]
    return any(k in text for k in keywords)


# ===================================================================
# XML REPORT BUILDER (con XSLT embebido para estilos profesionales)
# ===================================================================

# Logo SVG embebido (escudo Marshaall)
MARSHAALL_SVG_LOGO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 220" width="60" height="66">
  <defs>
    <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f1b2d"/>
      <stop offset="50%" style="stop-color:#1a2744"/>
      <stop offset="100%" style="stop-color:#3b82f6"/>
    </linearGradient>
  </defs>
  <path d="M100 10L20 50v70c0 50 35 85 80 95c45-10 80-45 80-95V50L100 10z" fill="url(#shieldGrad)" stroke="#60a5fa" stroke-width="2"/>
  <path d="M100 10L20 50v70c0 50 35 85 80 95V10z" fill="#0f1b2d" opacity="0.7"/>
  <line x1="40" y1="90" x2="90" y2="70" stroke="#22d3ee" stroke-width="2.5" opacity="0.8"/>
  <line x1="40" y1="110" x2="90" y2="90" stroke="#60a5fa" stroke-width="2" opacity="0.6"/>
  <line x1="110" y1="70" x2="160" y2="90" stroke="#22d3ee" stroke-width="2.5" opacity="0.8"/>
  <line x1="110" y1="90" x2="160" y2="110" stroke="#60a5fa" stroke-width="2" opacity="0.6"/>
  <polygon points="80,65 95,55 95,80 80,90" fill="#22d3ee" opacity="0.5"/>
  <polygon points="105,55 120,65 120,90 105,80" fill="#3b82f6" opacity="0.5"/>
</svg>"""

# SVG simplificado SIN linearGradient (seguro para WeasyPrint PDF)
MARSHAALL_PDF_SAFE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 220" width="60" height="66">
  <path d="M100 10L20 50v70c0 50 35 85 80 95c45-10 80-45 80-95V50L100 10z" fill="#1a2744" stroke="#60a5fa" stroke-width="2"/>
  <path d="M100 10L20 50v70c0 50 35 85 80 95V10z" fill="#0f1b2d" opacity="0.7"/>
  <line x1="40" y1="90" x2="90" y2="70" stroke="#22d3ee" stroke-width="2.5" opacity="0.8"/>
  <line x1="40" y1="110" x2="90" y2="90" stroke="#60a5fa" stroke-width="2" opacity="0.6"/>
  <line x1="110" y1="70" x2="160" y2="90" stroke="#22d3ee" stroke-width="2.5" opacity="0.8"/>
  <line x1="110" y1="90" x2="160" y2="110" stroke="#60a5fa" stroke-width="2" opacity="0.6"/>
  <polygon points="80,65 95,55 95,80 80,90" fill="#22d3ee" opacity="0.5"/>
  <polygon points="105,55 120,65 120,90 105,80" fill="#3b82f6" opacity="0.5"/>
</svg>"""


# ---------- Logo embebido en Base64 para reportes ----------
_LOGO_BASE64_CACHE = None
_LOGO_PDF_SAFE_CACHE = None


def _load_logo_base64(for_pdf=False):
    """Carga y cachea el logo como Base64 para incrustar en reportes HTML.
    Si for_pdf=True, usa un SVG sin gradientes como fallback seguro para WeasyPrint."""
    global _LOGO_BASE64_CACHE, _LOGO_PDF_SAFE_CACHE

    # Si ya tenemos la versión cacheada correcta, devolverla
    if not for_pdf and _LOGO_BASE64_CACHE is not None:
        return _LOGO_BASE64_CACHE
    if for_pdf and _LOGO_PDF_SAFE_CACHE is not None:
        return _LOGO_PDF_SAFE_CACHE

    # Intentar cargar el PNG real y redimensionarlo con PIL
    logo_paths = [
        "/usr/share/nginx/html/imagenes/logotipo.png",  # dentro del contenedor nginx (montado)
        os.path.join(os.path.dirname(__file__), "..", "frontend", "imagenes", "logotipo.png"),  # desarrollo local
    ]
    for logo_path in logo_paths:
        try:
            if not os.path.exists(logo_path):
                continue
            try:
                from PIL import Image
                img = Image.open(logo_path)
                # Redimensionar para que el alto sea 80px, manteniendo proporcion
                ratio = 80 / img.height
                new_w = int(img.width * ratio)
                img = img.resize((new_w, 80), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode()
                _LOGO_BASE64_CACHE = '<div class="logo-wrap"><img src="data:image/png;base64,{}" alt="Marshaall" style="height:60px;width:auto;object-fit:contain;"></div>'.format(b64)
                log.info("Logo embebido cargado (PIL, %d bytes base64)", len(b64))
                return _LOGO_BASE64_CACHE
            except ImportError:
                # Sin PIL, leer el archivo directamente (puede ser grande)
                with open(logo_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                _LOGO_BASE64_CACHE = '<div class="logo-wrap"><img src="data:image/png;base64,{}" alt="Marshaall" style="height:60px;width:auto;object-fit:contain;"></div>'.format(b64)
                log.info("Logo embebido cargado (sin PIL, %d bytes base64)", len(b64))
                return _LOGO_BASE64_CACHE
        except Exception as e:
            log.warning("No se pudo cargar logo desde %s: %s", logo_path, e)
            continue

    # Fallback: usar SVG del escudo
    if for_pdf:
        # Para PDF: usar SVG sin gradientes (seguro para WeasyPrint)
        _LOGO_PDF_SAFE_CACHE = MARSHAALL_PDF_SAFE_SVG.replace('"', "'")
        log.info("Usando SVG PDF-safe (sin gradientes) como logo del reporte")
        return _LOGO_PDF_SAFE_CACHE
    else:
        _LOGO_BASE64_CACHE = MARSHAALL_SVG_LOGO.replace('"', "'")
        log.info("Usando SVG de escudo como logo del reporte")
        return _LOGO_BASE64_CACHE

# Hoja de estilos XSLT para transformar el XML en HTML profesional
REPORT_XSLT = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:template match="/report">
<html lang="es">
<head>
<meta charset="UTF-8"/>
<title>Marshaall — Reporte de Seguridad</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:#eef1f6;color:#1a2744;-webkit-font-smoothing:antialiased;font-size:14px;line-height:1.5}
.page{max-width:1100px;margin:0 auto;padding:32px 24px}
/* Header — matches UI sidebar dark navy */
.header{background:linear-gradient(135deg,#0a0f1e 0%,#0f1b2d 40%,#1a2744 100%);border-radius:12px;padding:32px 40px;margin-bottom:24px;display:flex;align-items:center;gap:24px;box-shadow:0 4px 24px rgba(10,15,30,0.35);border:1px solid rgba(59,130,246,0.12)}
.header-logo{flex-shrink:0}
.logo-wrap{display:inline-flex;align-items:center;justify-content:center;border-radius:12px;padding:6px 18px}
.logo-wrap img{display:block}
.header-info{flex:1}
.header-title{font-size:28px;font-weight:700;color:#fff;letter-spacing:1.5px;margin-bottom:2px}
.header-subtitle{font-size:13px;color:#60a5fa;font-weight:500;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px}
.header-meta{display:flex;gap:24px;flex-wrap:wrap}
.header-meta span{font-size:12px;color:#94a3b8}
.header-meta strong{color:#e2e8f4}
.header-badge{background:#3b82f6;color:#fff;padding:6px 16px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-left:auto;align-self:flex-start;box-shadow:0 2px 8px rgba(59,130,246,0.25)}
/* Summary cards — navy-tinted borders matching UI accent */
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.summary-card{background:#fff;border-radius:8px;padding:18px 20px;box-shadow:0 1px 3px rgba(10,15,30,0.06);border:1px solid rgba(59,130,246,0.1)}
.summary-card .label{font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}
.summary-card .value{font-size:28px;font-weight:700;color:#1a2744}
.summary-card .value.blue{color:#3b82f6}
.summary-card .value.red{color:#ef4444}
.summary-card .value.orange{color:#f59e0b}
.summary-card .value.green{color:#22c55e}
/* Severity bar — exact UI token colors */
.sev-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:24px;background:#dde3ed}
.sev-bar .seg{height:100%}
.sev-s1{background:#ef4444}.sev-s2{background:#f59e0b}.sev-s3{background:#eab308}.sev-sn{background:#94a3b8}
/* Table — navy-tinted consistent with UI */
.table-section{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(10,15,30,0.06);border:1px solid rgba(59,130,246,0.1);overflow:hidden;margin-bottom:24px}
.table-header{padding:16px 24px;border-bottom:1px solid rgba(59,130,246,0.1);display:flex;align-items:center;justify-content:space-between}
.table-header h2{font-size:15px;font-weight:600;color:#1a2744}
.table-header .count{font-size:12px;color:#64748b;background:#eef1f6;padding:3px 10px;border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{text-align:left;padding:10px 16px;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;background:#f0f4f8;border-bottom:2px solid rgba(59,130,246,0.1)}
tbody td{padding:10px 16px;border-bottom:1px solid #eef1f6;color:#374151}
tbody tr:nth-child(even){background:#f8fafc}
/* Badges — consistent with UI tokens: red/orange/yellow */
.type-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.type-alert{background:rgba(239,68,68,0.1);color:#ef4444}
.type-flow{background:rgba(59,130,246,0.1);color:#3b82f6}
.type-stats{background:rgba(34,197,94,0.1);color:#22c55e}
.type-tls{background:rgba(234,179,8,0.1);color:#eab308}
.type-dns{background:rgba(124,58,237,0.1);color:#7c3aed}
.sev-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.sev-1{background:rgba(239,68,68,0.12);color:#ef4444}.sev-2{background:rgba(245,158,11,0.12);color:#f59e0b}.sev-3{background:rgba(234,179,8,0.12);color:#eab308}
/* Footer — branded */
.footer{text-align:center;padding:24px;color:#94a3b8;font-size:12px;border-top:1px solid rgba(59,130,246,0.08)}
.footer strong{color:#3b82f6}
/* Print styles */
@media print{
  body{background:#fff}
  .header{box-shadow:none;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .page{padding:0}
  .table-section,.summary-card{box-shadow:none}
}
</style>
</head>
<body>
<div class="page">
  <!-- Header con Logo -->
  <div class="header">
    <div class="header-logo">
      <div class="logo-wrap">
      """ + MARSHAALL_SVG_LOGO.replace('"', "'") + """
      </div>
    </div>
    <div class="header-info">
      <div class="header-title">MARSHAALL</div>
      <div class="header-subtitle">Reporte de Seguridad</div>
      <div class="header-meta">
        <span>Generado: <strong><xsl:value-of select="@generated_at"/></strong></span>
        <span>Desde: <strong><xsl:value-of select="@range_from"/></strong></span>
        <span>Hasta: <strong><xsl:value-of select="@range_to"/></strong></span>
      </div>
    </div>
    <div class="header-badge">
      <xsl:value-of select="@total"/> eventos
    </div>
  </div>

  <!-- Summary Cards -->
  <div class="summary">
    <div class="summary-card"><div class="label">Total Eventos</div><div class="value"><xsl:value-of select="summary/total_events"/></div></div>
    <div class="summary-card"><div class="label">Total Alertas</div><div class="value blue"><xsl:value-of select="summary/total_alerts"/></div></div>
    <div class="summary-card"><div class="label">Sev. Alta</div><div class="value red"><xsl:value-of select="summary/by_severity/sev_1"/></div></div>
    <div class="summary-card"><div class="label">Sev. Media</div><div class="value orange"><xsl:value-of select="summary/by_severity/sev_2"/></div></div>
    <div class="summary-card"><div class="label">Sev. Baja</div><div class="value green"><xsl:value-of select="summary/by_severity/sev_3"/></div></div>
    <div class="summary-card"><div class="label">Sin sev.</div><div class="value"><xsl:value-of select="summary/by_severity/sev_none"/></div></div>
  </div>

  <!-- Severity distribution bar -->
  <div class="sev-bar">
    <xsl:if test="summary/by_severity/sev_1 &gt; 0"><div class="seg sev-s1"><xsl:attribute name="style">width:<xsl:value-of select="round(summary/by_severity/sev_1 div summary/total_events * 100)"/>%</xsl:attribute></div></xsl:if>
    <xsl:if test="summary/by_severity/sev_2 &gt; 0"><div class="seg sev-s2"><xsl:attribute name="style">width:<xsl:value-of select="round(summary/by_severity/sev_2 div summary/total_events * 100)"/>%</xsl:attribute></div></xsl:if>
    <xsl:if test="summary/by_severity/sev_3 &gt; 0"><div class="seg sev-s3"><xsl:attribute name="style">width:<xsl:value-of select="round(summary/by_severity/sev_3 div summary/total_events * 100)"/>%</xsl:attribute></div></xsl:if>
    <xsl:if test="summary/by_severity/sev_none &gt; 0"><div class="seg sev-sn"><xsl:attribute name="style">width:<xsl:value-of select="round(summary/by_severity/sev_none div summary/total_events * 100)"/>%</xsl:attribute></div></xsl:if>
  </div>

  <!-- Events Table -->
  <div class="table-section">
    <div class="table-header">
      <h2>Detalle de Eventos</h2>
      <span class="count"><xsl:value-of select="@total"/> registros</span>
    </div>
    <table>
      <thead><tr>
        <th>ID</th><th>Fecha</th><th>Tipo</th><th>IP Origen</th><th>IP Destino</th>
        <th>Proto</th><th>Puerto Orig.</th><th>Puerto Dest.</th><th>Firma</th><th>Sev.</th>
      </tr></thead>
      <tbody>
        <xsl:for-each select="events/event">
        <tr>
          <td><xsl:value-of select="id"/></td>
          <td><xsl:value-of select="substring(timestamp,1,19)"/></td>
          <td>
            <xsl:choose>
              <xsl:when test="event_type='alert'"><span class="type-badge type-alert">alert</span></xsl:when>
              <xsl:when test="event_type='flow'"><span class="type-badge type-flow">flow</span></xsl:when>
              <xsl:when test="event_type='stats'"><span class="type-badge type-stats">stats</span></xsl:when>
              <xsl:when test="event_type='tls'"><span class="type-badge type-tls">tls</span></xsl:when>
              <xsl:when test="event_type='dns'"><span class="type-badge type-dns">dns</span></xsl:when>
              <xsl:otherwise><span class="type-badge"><xsl:value-of select="event_type"/></span></xsl:otherwise>
            </xsl:choose>
          </td>
          <td><xsl:value-of select="src_ip"/></td>
          <td><xsl:value-of select="dest_ip"/></td>
          <td><xsl:value-of select="proto"/></td>
          <td><xsl:value-of select="src_port"/></td>
          <td><xsl:value-of select="dest_port"/></td>
          <td><xsl:value-of select="signature"/></td>
          <td>
            <xsl:if test="severity != ''">
              <xsl:choose>
                <xsl:when test="severity='1'"><span class="sev-badge sev-1">Alta</span></xsl:when>
                <xsl:when test="severity='2'"><span class="sev-badge sev-2">Media</span></xsl:when>
                <xsl:when test="severity='3'"><span class="sev-badge sev-3">Baja</span></xsl:when>
                <xsl:otherwise><span class="sev-badge"><xsl:value-of select="severity"/></span></xsl:otherwise>
              </xsl:choose>
            </xsl:if>
          </td>
        </tr>
        </xsl:for-each>
      </tbody>
    </table>
  </div>

  <!-- Footer -->
  <div class="footer">
    Reporte generado automaticamente por <strong>Marshaall Cybersecurity Software</strong>
    <br/>Este documento es confidencial y de uso exclusivo para el analisis de seguridad.
  </div>
</div>
</body>
</html>
</xsl:template>
</xsl:stylesheet>"""


def build_report_xml(events, summary, meta):
    """Construye un XML de reporte con XSLT embebido para visualización profesional."""
    # Construir XML manualmente para incluir processing instruction de XSLT
    lines = []
    lines.append('<?xml version="1.0" encoding="utf-8"?>')
    lines.append('<?xml-stylesheet type="text/xsl" href="/api/reports/style.xsl"?>')
    lines.append('<report generated_at="{}" range_from="{}" range_to="{}" total="{}">'.format(
        _esc_attr(meta["generated_at"]),
        _esc_attr(meta["range_from"]),
        _esc_attr(meta["range_to"]),
        meta["total"],
    ))

    # Summary
    lines.append("  <summary>")
    lines.append("    <total_events>{}</total_events>".format(summary.get("total_events", 0)))
    lines.append("    <total_alerts>{}</total_alerts>".format(summary.get("total_alerts", 0)))
    lines.append("    <by_severity>")
    for k in ("sev_1", "sev_2", "sev_3", "sev_none"):
        lines.append("      <{}>{}</{}>".format(k, summary.get(k, 0), k))
    lines.append("    </by_severity>")
    lines.append("  </summary>")

    # Events
    lines.append("  <events>")
    for ev in events:
        lines.append("    <event>")
        lines.append("      <id>{}</id>".format(_esc_xml(ev.get("id", ""))))
        lines.append("      <timestamp>{}</timestamp>".format(_esc_xml(ev.get("ts", ""))))
        lines.append("      <event_type>{}</event_type>".format(_esc_xml(ev.get("event_type", ""))))
        lines.append("      <src_ip>{}</src_ip>".format(_esc_xml(ev.get("src_ip", ""))))
        lines.append("      <dest_ip>{}</dest_ip>".format(_esc_xml(ev.get("dest_ip", ""))))
        lines.append("      <proto>{}</proto>".format(_esc_xml(ev.get("proto", ""))))
        lines.append("      <src_port>{}</src_port>".format(_esc_xml(ev.get("src_port", "") or "")))
        lines.append("      <dest_port>{}</dest_port>".format(_esc_xml(ev.get("dest_port", "") or "")))
        if ev.get("event_type") == "alert":
            lines.append("      <signature>{}</signature>".format(_esc_xml(ev.get("signature", "") or "")))
            lines.append("      <severity>{}</severity>".format(_esc_xml(ev.get("severity", "") or "")))
            lines.append("      <category>{}</category>".format(_esc_xml(ev.get("category", "") or "")))
        lines.append("    </event>")
    lines.append("  </events>")
    lines.append("</report>")

    return "\n".join(lines).encode("utf-8")


def _esc_xml(val):
    """Escapa caracteres especiales para contenido XML."""
    s = str(val) if val is not None else ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_attr(val):
    """Escapa caracteres especiales para atributos XML."""
    s = str(val) if val is not None else ""
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


# ===================================================================
# ENDPOINTS
# ===================================================================

@app.get("/api/health")
@auth_required(min_role="admin")
def health():
    result = {"api": "ok"}
    try:
        conn = db()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        result["db"] = "ok"
    except Exception as e:
        result["db"] = "error: {}".format(e)
    try:
        with db().cursor() as cur:
            cur.execute("SELECT MAX(ts) AS last_event FROM events")
            row = cur.fetchone()
            if row and row["last_event"]:
                result["last_event"] = str(row["last_event"])
                cur.execute("SELECT TIMESTAMPDIFF(SECOND, MAX(ts), NOW()) AS lag FROM events")
                lag_row = cur.fetchone()
                lag = lag_row["lag"] if lag_row else None
                result["ingest_lag_seconds"] = lag
                result["ingest"] = "activa" if lag and lag < 300 else "inactiva"
            else:
                result["last_event"] = None
                result["ingest"] = "sin datos"
    except Exception:
        result["ingest"] = "desconocido"
    return jsonify(result)


@app.post("/api/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Faltan credenciales"}), 400
    with db().cursor() as cur:
        cur.execute("SELECT username, password_hash, role, active FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
    if not row:
        return jsonify({"error": "Usuario o contrasena incorrectos"}), 401
    if not row.get("active", 1):
        return jsonify({"error": "Cuenta desactivada"}), 403
    if not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Usuario o contrasena incorrectos"}), 401
    token = make_token(username, row["role"])
    return jsonify({"token": token, "username": username, "role": row["role"]})


@app.get("/api/events")
@auth_required()
def events():
    page, per_page = paginated_args()
    offset = (page - 1) * per_page
    with db().cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM events")
        total = cur.fetchone()["total"]
        cur.execute(
            "SELECT id, ts, event_type, src_ip, dest_ip, proto, signature,"
            " severity, flow_id, src_port, dest_port, category"
            " FROM events ORDER BY id DESC LIMIT %s OFFSET %s",
            (per_page, offset))
        rows = cur.fetchall()
    return jsonify({"data": rows, "total": total, "page": page, "per_page": per_page})


@app.get("/api/alerts")
@auth_required()
def alerts_list():
    page, per_page = paginated_args()
    offset = (page - 1) * per_page
    severity  = request.args.get("severity")
    category  = request.args.get("category")
    status    = request.args.get("status")
    q         = request.args.get("q")
    alert_id  = request.args.get("id")
    date_from = request.args.get("from")
    date_to   = request.args.get("to")
    where = ["e.event_type = 'alert'"]
    params = []
    if alert_id:
        where.append("e.id = %s")
        params.append(alert_id)
    if severity:
        where.append("e.severity = %s")
        params.append(int(severity))
    if category:
        where.append("e.category LIKE %s")
        params.append("%{}%".format(category))
    if status:
        where.append("COALESCE(s.status, 'nueva') = %s")
        params.append(status)
    if q:
        if q.isdigit():
            where.append("(e.id = %s OR e.signature LIKE %s OR e.src_ip LIKE %s OR e.dest_ip LIKE %s)")
            params.append(int(q))
            like = "%{}%".format(q)
            params.extend([like, like, like])
        else:
            where.append("(e.signature LIKE %s OR e.src_ip LIKE %s OR e.dest_ip LIKE %s)")
            like = "%{}%".format(q)
            params.extend([like, like, like])
    if date_from:
        where.append("e.ts >= %s")
        params.append(date_from)
    if date_to:
        where.append("e.ts <= %s")
        params.append(date_to)
    where_clause = " AND ".join(where)
    with db().cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM events e LEFT JOIN alert_status s ON s.event_id=e.id WHERE " + where_clause, params)
        total = cur.fetchone()["total"]
        cur.execute(
            "SELECT e.id, e.ts, e.src_ip, e.dest_ip, e.proto, e.signature,"
            " e.severity, e.category, e.flow_id, e.src_port, e.dest_port,"
            " COALESCE(s.status, 'nueva') AS status,"
            " s.assigned_to, s.updated_at AS status_updated"
            " FROM events e LEFT JOIN alert_status s ON s.event_id = e.id"
            " WHERE " + where_clause + " ORDER BY e.id DESC LIMIT %s OFFSET %s",
            params + [per_page, offset])
        rows = cur.fetchall()
    for r in rows:
        r["is_critical"] = is_critical_alert(r.get("signature", ""), r.get("category", ""))
    return jsonify({"data": rows, "total": total, "page": page, "per_page": per_page})


@app.get("/api/alerts/<int:alert_id>")
@auth_required()
def alert_detail(alert_id):
    with db().cursor() as cur:
        cur.execute(
            "SELECT e.*, COALESCE(s.status, 'nueva') AS status,"
            " s.assigned_to, s.updated_at AS status_updated, s.updated_by"
            " FROM events e LEFT JOIN alert_status s ON s.event_id = e.id"
            " WHERE e.id = %s AND e.event_type = 'alert'", (alert_id,))
        alert = cur.fetchone()
        if not alert:
            return jsonify({"error": "Alerta no encontrada"}), 404
        cur.execute("SELECT id, author, body, created_at FROM alert_comments WHERE event_id = %s ORDER BY created_at ASC", (alert_id,))
        comments = cur.fetchall()
        related = []
        if alert.get("flow_id"):
            cur.execute("SELECT id, ts, event_type, src_ip, dest_ip, proto, signature, severity FROM events WHERE flow_id = %s AND id != %s ORDER BY ts ASC LIMIT 50", (alert["flow_id"], alert_id))
            related = cur.fetchall()
        cur.execute("SELECT i.id, i.title, i.status, i.severity FROM incidents i JOIN incident_alerts ia ON ia.incident_id = i.id WHERE ia.event_id = %s", (alert_id,))
        incidents = cur.fetchall()
        alert["is_critical"] = is_critical_alert(alert.get("signature", ""), alert.get("category", ""))
    return jsonify({"alert": alert, "comments": comments, "related_events": related, "incidents": incidents})


@app.route("/api/alerts/<int:alert_id>/status", methods=["PATCH"])
@auth_required(min_role="analista")
def alert_update_status(alert_id):
    data = request.get_json(force=True, silent=True) or {}
    new_status = data.get("status")
    valid = ("nueva", "investigacion", "cerrada")
    if new_status not in valid:
        return jsonify({"error": "Estado invalido"}), 400
    with db().cursor() as cur:
        cur.execute("INSERT INTO alert_status (event_id, status, updated_by) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE status=%s, updated_by=%s",
                    (alert_id, new_status, g.user, new_status, g.user))
    return jsonify({"ok": True, "status": new_status})


@app.post("/api/alerts/<int:alert_id>/comments")
@auth_required(min_role="analista")
def alert_add_comment(alert_id):
    data = request.get_json(force=True, silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Comentario vacio"}), 400
    with db().cursor() as cur:
        cur.execute("INSERT INTO alert_comments (event_id, author, body) VALUES (%s, %s, %s)", (alert_id, g.user, body))
    return jsonify({"ok": True}), 201


@app.get("/api/incidents")
@auth_required()
def incidents_list():
    page, per_page = paginated_args()
    offset = (page - 1) * per_page
    status = request.args.get("status")
    where = "1=1"
    params = []
    if status:
        where = "status = %s"
        params.append(status)
    with db().cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM incidents WHERE " + where, params)
        total = cur.fetchone()["total"]
        cur.execute(
            "SELECT i.*, (SELECT COUNT(*) FROM incident_alerts WHERE incident_id=i.id) AS alert_count, "
            "(SELECT GROUP_CONCAT(e.signature) FROM incident_alerts ia JOIN events e ON e.id = ia.event_id WHERE ia.incident_id = i.id) AS sigs "
            "FROM incidents i WHERE " + where + " ORDER BY i.updated_at DESC LIMIT %s OFFSET %s", params + [per_page, offset])
        rows = cur.fetchall()
    for r in rows:
        r["is_critical"] = is_critical_alert(r.get("sigs") or "", "")
    return jsonify({"data": rows, "total": total, "page": page, "per_page": per_page})


@app.post("/api/incidents")
@auth_required(min_role="analista")
def incident_create():
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Titulo requerido"}), 400
    description = data.get("description", "")
    severity = parse_int(data.get("severity"), 3, 1, 5)
    tags = data.get("tags", "")
    with db().cursor() as cur:
        cur.execute("INSERT INTO incidents (title, description, severity, created_by, tags) VALUES (%s, %s, %s, %s, %s)", (title, description, severity, g.user, tags))
        incident_id = cur.lastrowid
    return jsonify({"ok": True, "id": incident_id}), 201


@app.get("/api/incidents/<int:incident_id>")
@auth_required()
def incident_detail(incident_id):
    with db().cursor() as cur:
        cur.execute("SELECT * FROM incidents WHERE id=%s", (incident_id,))
        inc = cur.fetchone()
        if not inc:
            return jsonify({"error": "Incidente no encontrado"}), 404
        cur.execute(
            "SELECT e.id, e.ts, e.src_ip, e.dest_ip, e.proto, e.signature, e.severity, e.category, COALESCE(s.status, 'nueva') AS status"
            " FROM incident_alerts ia JOIN events e ON e.id = ia.event_id LEFT JOIN alert_status s ON s.event_id = e.id"
            " WHERE ia.incident_id = %s ORDER BY e.ts DESC", (incident_id,))
        alerts = cur.fetchall()
        cur.execute("SELECT id, author, body, created_at FROM incident_comments WHERE incident_id=%s ORDER BY created_at ASC", (incident_id,))
        comments = cur.fetchall()
    return jsonify({"incident": inc, "alerts": alerts, "comments": comments})


@app.route("/api/incidents/<int:incident_id>", methods=["PATCH"])
@auth_required(min_role="analista")
def incident_update(incident_id):
    data = request.get_json(force=True, silent=True) or {}
    fields = []
    params = []
    for col in ("title", "description", "tags"):
        if col in data:
            fields.append(col + "=%s")
            params.append(data[col])
    if "severity" in data:
        fields.append("severity=%s")
        params.append(parse_int(data["severity"], 3, 1, 5))
    if "status" in data:
        valid = ("abierto", "en_progreso", "cerrado")
        if data["status"] not in valid:
            return jsonify({"error": "Estado invalido"}), 400
        fields.append("status=%s")
        params.append(data["status"])
    if not fields:
        return jsonify({"error": "Nada que actualizar"}), 400
    params.append(incident_id)
    with db().cursor() as cur:
        cur.execute("UPDATE incidents SET " + ", ".join(fields) + " WHERE id=%s", params)
    return jsonify({"ok": True})


@app.post("/api/incidents/<int:incident_id>/alerts")
@auth_required(min_role="analista")
def incident_add_alerts(incident_id):
    data = request.get_json(force=True, silent=True) or {}
    event_ids = data.get("event_ids", [])
    if not event_ids or not isinstance(event_ids, list):
        return jsonify({"error": "event_ids requerido (array)"}), 400
    with db().cursor() as cur:
        for eid in event_ids:
            try:
                cur.execute("INSERT IGNORE INTO incident_alerts (incident_id, event_id, added_by) VALUES (%s, %s, %s)", (incident_id, int(eid), g.user))
            except Exception:
                pass
    return jsonify({"ok": True}), 201


@app.route("/api/incidents/<int:incident_id>/alerts/<int:event_id>", methods=["DELETE"])
@auth_required(min_role="analista")
def incident_remove_alert(incident_id, event_id):
    with db().cursor() as cur:
        cur.execute("DELETE FROM incident_alerts WHERE incident_id=%s AND event_id=%s", (incident_id, event_id))
    return jsonify({"ok": True})


@app.post("/api/incidents/<int:incident_id>/comments")
@auth_required(min_role="analista")
def incident_add_comment(incident_id):
    data = request.get_json(force=True, silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Comentario vacio"}), 400
    with db().cursor() as cur:
        cur.execute("INSERT INTO incident_comments (incident_id, author, body) VALUES (%s, %s, %s)", (incident_id, g.user, body))
    return jsonify({"ok": True}), 201


@app.get("/api/correlation/suggestions")
@auth_required(min_role="analista")
def correlation_suggestions():
    minutes = parse_int(request.args.get("minutes"), 30, 5, 1440)
    threshold = parse_int(request.args.get("threshold"), 5, 2, 100)
    with db().cursor() as cur:
        cur.execute(
            "SELECT e.signature, e.src_ip, COUNT(*) AS cnt,"
            " MIN(e.ts) AS first_seen, MAX(e.ts) AS last_seen,"
            " GROUP_CONCAT(e.id ORDER BY e.ts SEPARATOR ',') AS event_ids"
            " FROM events e LEFT JOIN incident_alerts ia ON ia.event_id = e.id"
            " WHERE e.event_type = 'alert' AND e.ts >= (NOW() - INTERVAL %s MINUTE) AND ia.event_id IS NULL"
            " GROUP BY e.signature, e.src_ip HAVING cnt >= %s ORDER BY cnt DESC LIMIT 20",
            (minutes, threshold))
        rows = cur.fetchall()
    for row in rows:
        if row.get("event_ids"):
            row["event_ids"] = [int(x) for x in row["event_ids"].split(",")]
    return jsonify(rows)


@app.get("/api/stats/events_per_minute")
@auth_required()
def events_per_minute():
    minutes = parse_int(request.args.get("minutes"), 60, 5, 10080)
    with db().cursor() as cur:
        cur.execute(
        "SELECT DATE_FORMAT(ts, '%%Y-%%m-%%d %%H:%%i:00') AS minute_bucket,"
        " COUNT(*) AS total,"
        " SUM(CASE WHEN severity = 1 THEN 1 ELSE 0 END) AS sev_1,"
        " SUM(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS sev_2,"
        " SUM(CASE WHEN severity = 3 THEN 1 ELSE 0 END) AS sev_3,"
        " SUM(CASE WHEN severity IS NULL THEN 1 ELSE 0 END) AS sev_none"
        " FROM events "
        " WHERE event_type = 'alert' "
        " AND ts >= (SELECT MAX(ts) FROM events WHERE event_type = 'alert') - INTERVAL %s MINUTE "
        " GROUP BY minute_bucket ORDER BY minute_bucket ASC",
        (minutes,))

        rows = cur.fetchall()
    return jsonify(rows)


@app.get("/api/stats/top_ips")
@auth_required()
def top_ips_stats():
    """Top IPs atacantes con total de alertas y severidad máxima."""
    limit = parse_int(request.args.get("limit"), 10, 1, 30)
    with db().cursor() as cur:
        cur.execute(
            "SELECT src_ip, COUNT(*) AS alert_count,"
            " MIN(COALESCE(severity, 4)) AS max_severity"
            " FROM events WHERE event_type = 'alert' AND src_ip IS NOT NULL"
            " GROUP BY src_ip ORDER BY alert_count DESC LIMIT %s",
            (limit,))
        rows = cur.fetchall()
    return jsonify(rows)


@app.get("/api/stats/summary")
@auth_required()
def stats_summary():
    with db().cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM events")
        total_events = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM events WHERE event_type='alert'")
        total_alerts = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM events e LEFT JOIN alert_status s ON s.event_id = e.id WHERE e.event_type='alert' AND COALESCE(s.status, 'nueva') = 'nueva'")
        open_alerts = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM incidents WHERE status != 'cerrado'")
        open_incidents = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM events WHERE ts >= (NOW() - INTERVAL 24 HOUR) AND event_type='alert'")
        events_24h = cur.fetchone()["total"]
    return jsonify({
        "total_events": total_events,
        "total_alerts": total_alerts,
        "open_alerts": open_alerts,
        "open_incidents": open_incidents,
        "events_24h": events_24h,
    })


@app.get("/api/stats/severity_distribution")
@auth_required()
def severity_distribution():
    """Distribución de alertas por severidad (para Doughnut chart)."""
    with db().cursor() as cur:
        cur.execute(
            "SELECT severity, COUNT(*) AS count FROM events"
            " WHERE event_type = 'alert' AND severity IS NOT NULL"
            " GROUP BY severity ORDER BY severity ASC"
        )
        rows = cur.fetchall()
    return jsonify(rows)


@app.get("/api/stats/attack_types")
@auth_required()
def attack_types_stats():
    """Top categorías/firmas de ataque detectadas (para Pie chart)."""
    with db().cursor() as cur:
        cur.execute(
            "SELECT COALESCE(NULLIF(category,''), SUBSTRING_INDEX(signature,' ',3), 'Desconocido') AS attack_type,"
            " COUNT(*) AS count FROM events"
            " WHERE event_type = 'alert'"
            " GROUP BY attack_type ORDER BY count DESC LIMIT 8"
        )
        rows = cur.fetchall()
    return jsonify(rows)


@app.get("/api/stats/top_ports")
@auth_required()
def top_ports_stats():
    """Puertos/servicios más atacados (para Polar Area chart)."""
    port_names = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Alt",
        8443: "HTTPS-Alt", 6379: "Redis", 27017: "MongoDB",
    }
    with db().cursor() as cur:
        cur.execute(
            "SELECT dest_port, COUNT(*) AS count FROM events"
            " WHERE event_type = 'alert' AND dest_port IS NOT NULL AND dest_port > 0"
            " GROUP BY dest_port ORDER BY count DESC LIMIT 8"
        )
        rows = cur.fetchall()
    result = []
    for r in rows:
        p = r["dest_port"]
        name = port_names.get(p, "")
        result.append({"dest_port": p, "service": name, "count": r["count"]})
    return jsonify(result)


@app.get("/api/stats/threat_intel")
@auth_required()
def threat_intel():
    """Endpoint para la nueva pestaña Inteligencia de Amenazas / Riesgos."""
    with db().cursor() as cur:
        # 1. Matriz de Riesgo (Incidentes Abiertos / En Progreso)
        # Calculamos Impacto (1 a 5, basado en la severidad del incidente)
        # Calculamos Urgencia (1 a 5, basado en la antiguedad de la última alerta y palabras clave críticas)
        cur.execute(
            "SELECT i.id, i.title, i.severity AS impact, i.created_at, i.updated_at, "
            " COUNT(ia.event_id) as event_count,"
            " GROUP_CONCAT(e.signature) as sigs,"
            " MAX(e.ts) as last_event_ts"
            " FROM incidents i "
            " LEFT JOIN incident_alerts ia ON ia.incident_id = i.id"
            " LEFT JOIN events e ON e.id = ia.event_id"
            " WHERE i.status != 'cerrado'"
            " GROUP BY i.id"
        )
        incidents = cur.fetchall()
        
        risk_matrix = []
        for inc in incidents:
            # Urgencia base: 1 (Baja), 2 (Media), 3 (Alta)
            urgency = 1
            if inc.get("last_event_ts"):
                # Menos de 24h -> Media
                if inc["last_event_ts"] > datetime.now() - timedelta(hours=24):
                    urgency = 2
                # Menos de 2h -> Alta
                if inc["last_event_ts"] > datetime.now() - timedelta(hours=2):
                    urgency = 3
            
            # Subir urgencia a 4 o 5 si es crítico
            if is_critical_alert(inc.get("sigs") or "", ""):
                urgency = min(urgency + 2, 5)

            risk_matrix.append({
                "id": inc["id"],
                "title": inc["title"],
                "impact": inc["impact"],  # 1 a 5
                "urgency": urgency,       # 1 a 5
                "event_count": inc["event_count"]
            })

        # 2. Probabilidad de Escalada (Atacantes Reincidentes)
        # Buscamos IPs que tienen múltiples alertas de diferente severidad
        cur.execute(
            "SELECT src_ip, COUNT(id) as alert_count,"
            " COUNT(DISTINCT severity) as sev_variance,"
            " MIN(severity) as max_severity,"
            " MIN(ts) as first_seen, MAX(ts) as last_seen"
            " FROM events WHERE event_type = 'alert' AND src_ip IS NOT NULL"
            " GROUP BY src_ip HAVING alert_count > 5 AND sev_variance > 1"
            " ORDER BY alert_count DESC, max_severity ASC LIMIT 10"
        )
        escalation_ips = cur.fetchall()

        for ip in escalation_ips:
            # Probabilidad de escalada (1 a 100) basada en varianza y volumen
            score = min(100, (ip["alert_count"] * 2) + (ip["sev_variance"] * 10))
            if ip["max_severity"] == 1:
                score = min(100, score + 20)
            ip["probability_score"] = score
            ip["phase"] = "Reconocimiento y Escalada" if ip["max_severity"] > 1 else "Ataque Crítico"

    return jsonify({
        "risk_matrix": risk_matrix,
        "escalation_ips": escalation_ips
    })


@app.get("/api/users")
@auth_required(min_role="admin")
def users_list():
    with db().cursor() as cur:
        cur.execute("SELECT id, username, role, active, created_at FROM users ORDER BY id ASC")
        rows = cur.fetchall()
    return jsonify(rows)


@app.post("/api/users")
@auth_required(min_role="admin")
def user_create():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "viewer")
    if not username or not password:
        return jsonify({"error": "Usuario y contrasena requeridos"}), 400
    if len(password) < 6:
        return jsonify({"error": "Contrasena minimo 6 caracteres"}), 400
    if role not in ("admin", "analista", "viewer"):
        return jsonify({"error": "Rol invalido"}), 400
    pwd_hash = generate_password_hash(password)
    try:
        with db().cursor() as cur:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", (username, pwd_hash, role))
    except pymysql.err.IntegrityError:
        return jsonify({"error": "El usuario ya existe"}), 409
    return jsonify({"ok": True}), 201


@app.route("/api/users/<int:user_id>", methods=["PATCH"])
@auth_required(min_role="admin")
def user_update(user_id):
    data = request.get_json(force=True, silent=True) or {}
    fields = []
    params = []
    if "role" in data:
        if data["role"] not in ("admin", "analista", "viewer"):
            return jsonify({"error": "Rol invalido"}), 400
        fields.append("role=%s")
        params.append(data["role"])
    if "active" in data:
        fields.append("active=%s")
        params.append(1 if data["active"] else 0)
    if "password" in data:
        pwd = data["password"]
        if len(pwd) < 6:
            return jsonify({"error": "Contrasena minimo 6 caracteres"}), 400
        fields.append("password_hash=%s")
        params.append(generate_password_hash(pwd))
    if not fields:
        return jsonify({"error": "Nada que actualizar"}), 400
    params.append(user_id)
    with db().cursor() as cur:
        cur.execute("UPDATE users SET " + ", ".join(fields) + " WHERE id=%s", params)
    return jsonify({"ok": True})


@app.get("/api/me")
@auth_required()
def me():
    return jsonify({"username": g.user, "role": g.role})


# ===================================================================
# REPORT ENDPOINTS (XML + HTML)
# ===================================================================

def _get_report_data(range_param, date_from_arg, date_to_arg, limit_arg):
    """Helper: Consulta eventos y summary para reportes.
    Usa datetime.now() (hora local del contenedor, TZ=Europe/Madrid)
    para coincidir con los timestamps almacenados en MariaDB."""
    range_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = range_map.get(range_param, timedelta(hours=24))
    now = datetime.now()
    ts_from = date_from_arg if date_from_arg else (now - delta).strftime("%Y-%m-%d %H:%M:%S")
    ts_to   = date_to_arg   if date_to_arg   else now.strftime("%Y-%m-%d %H:%M:%S")
    limit   = parse_int(limit_arg, 5000, 1, 50000)
    log.info("Report query range: %s -> %s (limit=%d, range=%s)", ts_from, ts_to, limit, range_param)

    with db().cursor() as cur:
        cur.execute(
            "SELECT id, ts, event_type, src_ip, dest_ip, proto,"
            " signature, severity, flow_id, src_port, dest_port, category"
            " FROM events WHERE ts >= %s AND ts <= %s"
            " ORDER BY ts DESC LIMIT %s",
            (ts_from, ts_to, limit)
        )
        rows = cur.fetchall()
        cur.execute(
            "SELECT COUNT(*) AS total_events,"
            " SUM(CASE WHEN event_type='alert' THEN 1 ELSE 0 END) AS total_alerts,"
            " SUM(CASE WHEN severity=1 THEN 1 ELSE 0 END) AS sev_1,"
            " SUM(CASE WHEN severity=2 THEN 1 ELSE 0 END) AS sev_2,"
            " SUM(CASE WHEN severity=3 THEN 1 ELSE 0 END) AS sev_3,"
            " SUM(CASE WHEN severity IS NULL THEN 1 ELSE 0 END) AS sev_none"
            " FROM events WHERE ts >= %s AND ts <= %s",
            (ts_from, ts_to)
        )
        summary_row = cur.fetchone()

    summary = {
        "total_events": summary_row["total_events"] or 0,
        "total_alerts": summary_row["total_alerts"] or 0,
        "sev_1": summary_row["sev_1"] or 0,
        "sev_2": summary_row["sev_2"] or 0,
        "sev_3": summary_row["sev_3"] or 0,
        "sev_none": summary_row["sev_none"] or 0,
    }
    meta = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range_from": str(ts_from),
        "range_to": str(ts_to),
        "total": len(rows),
        "now": now,
    }
    return rows, summary, meta


@app.get("/api/reports/events.xml")
@auth_required(min_role="analista")
def report_events_xml():
    """Genera y descarga un reporte XML de eventos/alertas."""
    try:
        rows, summary, meta = _get_report_data(
            request.args.get("range", "24h"),
            request.args.get("from"),
            request.args.get("to"),
            request.args.get("limit"),
        )
        xml_bytes = build_report_xml(rows, summary, meta)
        filename = "marshaall_report_{}.xml".format(meta["now"].strftime("%Y%m%d_%H%M%S"))
        return Response(
            xml_bytes,
            mimetype="application/xml",
            headers={"Content-Disposition": "inline; filename={}".format(filename)},
        )
    except Exception as e:
        log.error("Error generando reporte XML: %s", e)
        return jsonify({"error": "Error generando el reporte"}), 500


@app.get("/api/reports/events.html")
@auth_required(min_role="analista")
def report_events_html():
    """Genera y descarga un reporte HTML de eventos/alertas (descarga directa)."""
    try:
        rows, summary, meta = _get_report_data(
            request.args.get("range", "24h"),
            request.args.get("from"),
            request.args.get("to"),
            request.args.get("limit"),
        )
        html_content, filename = _build_report_html(rows, summary, meta, extra=_get_report_extra(db()))
        return Response(
            html_content.encode("utf-8"),
            mimetype="text/html",
            headers={
                "Content-Disposition": "attachment; filename={}".format(filename),
                "Content-Type": "text/html; charset=utf-8",
            },
        )

    except Exception as e:
        log.error("Error generando reporte HTML: %s", e)
        return jsonify({"error": "Error generando el reporte"}), 500


def _build_report_html(rows, summary, meta, for_pdf=False, extra=None):
    """Genera un HTML profesional y corporativo optimizado para WeasyPrint."""
    gen_date = meta["now"].strftime("%d de %B, %Y - %H:%M:%S")
    gen_date_short = meta["now"].strftime("%d/%m/%Y %H:%M")
    filename = "marshaall_report_{}.pdf".format(meta["now"].strftime("%Y%m%d_%H%M%S"))
    extra = extra or {}

    # Prepare alerts HTML
    alerts_html = ""
    alert_rows = [r for r in rows if r.get("event_type") == "alert"]
    for r in alert_rows:
        sev_class = "sev-alta" if r["severity"] == 1 else "sev-media" if r["severity"] == 2 else "sev-baja"
        sev_label = "ALTA" if r["severity"] == 1 else "MEDIA" if r["severity"] == 2 else "BAJA"
        ts = r["ts"].strftime("%d/%m %H:%M") if hasattr(r["ts"], "strftime") else str(r["ts"])
        alerts_html += f"""
        <tr>
          <td>{r['id']}</td>
          <td>{ts}</td>
          <td>{_esc_xml(r['src_ip'])}</td>
          <td>{_esc_xml(r['dest_ip'])}</td>
          <td class="sig">{_esc_xml(r['signature'])}</td>
          <td><span class="sev {sev_class}">{sev_label}</span></td>
        </tr>"""

    # Prepare top IPs
    top_ips_html = ""
    for ip in extra.get("top_ips", []):
        sev_color = "#dc2626" if ip["max_severity"] == 1 else "#d97706" if ip["max_severity"] == 2 else "#3b82f6"
        top_ips_html += f'<tr><td>{_esc_xml(ip["src_ip"])}</td><td>{ip["alert_count"]}</td><td style="color:{sev_color}">●</td></tr>'

    # Prepare top attacks (Translated)
    attack_map = {
        "A Network Trojan was detected": "Troyano de red detectado",
        "Attempted Information Leak": "Intento de fuga de información",
        "Information Leak": "Fuga de información",
        "Network Trojan": "Troyano de red",
        "Misc activity": "Actividad diversa",
        "Misc Attack": "Ataque diverso",
        "Potentially Bad Traffic": "Tráfico potencialmente malicioso",
        "Bad Traffic": "Tráfico malicioso",
        "Web Application Attack": "Ataque a aplicación web",
        "Attempted Denial of Service": "Intento de denegación de servicio",
        "Denial of Service": "Denegación de servicio",
        "Detection of a Network Scan": "Escaneo de red detectado",
        "Network Scan": "Escaneo de red",
        "Attempted User Privilege Gain": "Intento de escalada de privilegios",
        "Attempted Administrator Privilege Gain": "Intento de acceso como administrador",
        "Successful Administrator Privilege Gain": "Acceso de administrador logrado",
        "Successful User Privilege Gain": "Escalada de privilegios lograda",
        "Decode of an RPC Query": "Decodificación de consulta RPC",
        "Executable Code was Detected": "Código ejecutable detectado",
        "A suspicious filename was detected": "Nombre de archivo sospechoso",
        "Not Suspicious Traffic": "Tráfico no sospechoso",
    }
    top_attacks_html = ""
    for at in extra.get("top_attacks", []):
        at_name = at["attack_type"]
        for en, es in attack_map.items():
            if en.lower() in at_name.lower():
                at_name = es
                break
        top_attacks_html += f'<tr><td>{_esc_xml(at_name)}</td><td>{at["count"]}</td></tr>'

    # Risk Logic
    total = max(summary["total_alerts"], 1)
    pct1 = round(summary["sev_1"] / total * 100)
    pct2 = round(summary["sev_2"] / total * 100)
    pct3 = round(summary["sev_3"] / total * 100)
    pctn = max(0, 100 - pct1 - pct2 - pct3)
    
    if pct1 > 10 or summary["sev_1"] > 20:
        risk_level = "CRÍTICO"; risk_color = "#ef4444"
    elif pct1 > 2 or summary["sev_1"] > 5 or pct2 > 20:
        risk_level = "ALTO"; risk_color = "#f97316"
    elif pct2 > 5 or pct1 > 0:
        risk_level = "MEDIO"; risk_color = "#f59e0b"
    else:
        risk_level = "BAJO"; risk_color = "#10b981"

    open_alerts = extra.get("open_alerts", 0)
    open_incidents = extra.get("open_incidents", 0)
    alert_ratio = round((summary["total_alerts"] / summary["total_events"] * 100), 1) if summary["total_events"] > 0 else 0

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
@page {{
    size: A4;
    margin: 2cm;
    @bottom-center {{
        content: "Marshaall Security — v2.6 — Página " counter(page);
        font-size: 9px;
        color: #94a3b8;
        border-top: 1px solid #e2e8f0;
        width: 100%;
        padding-top: 10px;
    }}
}}
body {{
  font-family: 'Helvetica', 'Arial', sans-serif;
  color: #1e293b; line-height: 1.4; margin: 0; padding: 0; background: #fff;
  font-size: 11px;
}}

/* ===== COVER PAGE ===== */
.cover {{
  height: 25cm; text-align: center; padding-top: 5cm;
}}
.cover-logo {{ margin-bottom: 2cm; }}
.cover-logo img {{ height: 80px; }}
.cover h1 {{
  font-size: 32px; font-weight: 700; color: #0f172a; margin: 0 0 10px 0;
  text-transform: uppercase; letter-spacing: 2px;
}}
.cover .subtitle {{
  font-size: 14px; color: #64748b; margin-bottom: 4cm;
  text-transform: uppercase; letter-spacing: 4px;
}}
.cover-meta-table {{
  width: 12cm; margin: 0 auto; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 8px; padding: 20px; text-align: left;
}}
.cover-meta-table td {{ padding: 5px 10px; font-size: 12px; }}
.cover-meta-table .label {{ font-weight: 700; color: #0f172a; width: 150px; }}

/* ===== SECTIONS ===== */
.section-header {{
  margin-top: 40px; margin-bottom: 20px; border-bottom: 2px solid #0f172a; padding-bottom: 10px;
}}
.section-title {{ font-size: 18px; font-weight: 700; color: #0f172a; text-transform: uppercase; }}
.section-num {{ font-size: 22px; font-weight: 800; color: #3b82f6; margin-right: 10px; }}

/* ===== KPI GRID (Using Table) ===== */
.kpi-table {{ width: 100%; border-collapse: separate; border-spacing: 10px; margin: 0 -10px; }}
.kpi-card {{
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 15px; text-align: center; width: 33.33%;
}}
.kpi-val {{ font-size: 24px; font-weight: 800; color: #0f172a; margin-bottom: 2px; }}
.kpi-label {{ font-size: 9px; color: #64748b; text-transform: uppercase; font-weight: 700; }}

/* ===== RISK BANNER (Using Table) ===== */
.risk-table {{ width: 100%; background: #f1f5f9; border-radius: 8px; margin-bottom: 30px; }}
.risk-table td {{ padding: 15px; vertical-align: middle; }}
.risk-badge {{
  background: {risk_color}; color: #fff; padding: 8px 12px;
  border-radius: 4px; font-weight: 800; font-size: 14px; text-align: center;
  display: block; width: 100px;
}}
.risk-desc {{ font-size: 12px; color: #334155; }}

/* ===== SEVERITY BAR ===== */
.bar-container {{ margin: 25px 0; }}
.bar-title {{ font-size: 11px; font-weight: 700; color: #0f172a; margin-bottom: 8px; margin-top: 0; }}
.bar-rail {{ height: 20px; background: #e2e8f0; border-radius: 10px; overflow: hidden; width: 100%; }}
.bar-seg {{ height: 100%; display: inline-block; float: left; }}
.bg-alta {{ background: #dc2626; }}.bg-media {{ background: #f59e0b; }}.bg-baja {{ background: #10b981; }}.bg-info {{ background: #94a3b8; }}

/* ===== DATA TABLES ===== */
.data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 0; }}
.data-table th {{
  background: #f1f5f9; color: #475569; text-align: left;
  padding: 8px 12px; font-size: 10px; font-weight: 700; text-transform: uppercase;
  border-bottom: 2px solid #e2e8f0;
}}
.data-table td {{ padding: 8px 12px; font-size: 11px; border-bottom: 1px solid #f1f5f9; }}
.data-table tr:nth-child(even) {{ background: #fcfdfe; }}

.sev {{ padding: 2px 5px; border-radius: 3px; font-size: 9px; font-weight: 700; color: #fff; }}
.sev-alta {{ background: #ef4444; }}.sev-media {{ background: #f59e0b; }}.sev-baja {{ background: #10b981; }}

.vector-container {{ margin-bottom: 20px; }}
.vector-cell {{ vertical-align: top; padding: 0; }}

.page-break {{ page-break-before: always; }}
</style>
</head>
<body>

<div class="page cover">
  <div class="cover-logo">{_load_logo_base64(for_pdf=for_pdf)}</div>
  <h1>Informe de Seguridad</h1>
  <p class="subtitle">Análisis de Amenazas Marshaall</p>
  
  <table class="cover-meta-table">
    <tr><td class="label">Fecha:</td><td>{gen_date}</td></tr>
    <tr><td class="label">Periodo:</td><td>{meta["range_from"]} - {meta["range_to"]}</td></tr>
    <tr><td class="label">Clasificación:</td><td>CONFIDENCIAL</td></tr>
    <tr><td class="label">Versión SIEM:</td><td>Marshaall v2.0</td></tr>
  </table>
</div>

<div class="page-break"></div>

<div class="content">
  <div class="section-header">
    <span class="section-num">01</span><span class="section-title">Resumen Ejecutivo</span>
  </div>

  <table class="risk-table">
    <tr>
      <td width="130"><div class="risk-badge">{risk_level}</div></td>
      <td class="risk-desc">
        El análisis de seguridad del periodo reporta un nivel de riesgo <strong>{risk_level}</strong>. 
        Se han procesado {summary["total_events"]} eventos, identificando {summary["total_alerts"]} alertas.
      </td>
    </tr>
  </table>

  <table class="kpi-table">
    <tr>
      <td class="kpi-card" style="border-top: 3px solid #3b82f6;">
        <div class="kpi-val">{summary["total_events"]}</div><div class="kpi-label">Eventos Totales</div>
      </td>
      <td class="kpi-card" style="border-top: 3px solid #ef4444;">
        <div class="kpi-val">{summary["sev_1"]}</div><div class="kpi-label">Alertas Críticas</div>
      </td>
      <td class="kpi-card" style="border-top: 3px solid #f59e0b;">
        <div class="kpi-val">{summary["sev_2"]}</div><div class="kpi-label">Alertas Medias</div>
      </td>
    </tr>
    <tr>
      <td class="kpi-card">
        <div class="kpi-val">{open_alerts}</div><div class="kpi-label">Alertas Pendientes</div>
      </td>
      <td class="kpi-card">
        <div class="kpi-val">{open_incidents}</div><div class="kpi-label">Casos Abiertos</div>
      </td>
      <td class="kpi-card">
        <div class="kpi-val">{alert_ratio}%</div><div class="kpi-label">Tasa de Alerta</div>
      </td>
    </tr>
  </table>

  <div class="bar-container">
    <div class="bar-title">Distribución de Severidad (%)</div>
    <div class="bar-rail">
      <div class="bar-seg bg-alta" style="width:{pct1}%"></div>
      <div class="bar-seg bg-media" style="width:{pct2}%"></div>
      <div class="bar-seg bg-baja" style="width:{pct3}%"></div>
      <div class="bar-seg bg-info" style="width:{pctn}%"></div>
    </div>
    <div style="margin-top:8px; font-size:9px; color:#64748b;">
      ● Alta ({summary["sev_1"]}) &nbsp;&nbsp; ● Media ({summary["sev_2"]}) &nbsp;&nbsp; ● Baja ({summary["sev_3"]})
    </div>
  </div>

  <div class="section-header" style="margin-top:40px">
    <span class="section-num">02</span><span class="section-title">Análisis de Vectores</span>
  </div>

  <table width="100%" cellspacing="0" cellpadding="0" style="table-layout: fixed; margin-top: 0;" class="vector-container">
    <tr>
      <td width="48%" class="vector-cell">
        <div class="bar-title">Top IPs de Origen</div>
        <table class="data-table">
          <thead><tr><th>IP</th><th width="50">Alertas</th><th width="30">Sev.</th></tr></thead>
          <tbody>{top_ips_html if top_ips_html else "<tr><td colspan='3'>Sin datos</td></tr>"}</tbody>
        </table>
      </td>
      <td width="4%"></td>
      <td width="48%" class="vector-cell">
        <div class="bar-title">Tipos de Amenaza</div>
        <table class="data-table">
          <thead><tr><th>Categoría</th><th width="50">Cant.</th></tr></thead>
          <tbody>{top_attacks_html if top_attacks_html else "<tr><td colspan='2'>Sin datos</td></tr>"}</tbody>
        </table>
      </td>
    </tr>
  </table>
</div>

<div class="page-break"></div>

<div class="content">
  <div class="section-header">
    <span class="section-num">03</span><span class="section-title">Registro de Alertas</span>
  </div>

  <table class="data-table" style="font-size:9px">
    <thead>
      <tr>
        <th width="40">ID</th>
        <th width="80">Fecha</th>
        <th width="100">Origen</th>
        <th width="100">Destino</th>
        <th>Firma de Seguridad</th>
        <th width="40">Sev.</th>
      </tr>
    </thead>
    <tbody>
      {alerts_html if alerts_html else "<tr><td colspan='6' style='text-align:center;'>No se detectaron alertas en este periodo</td></tr>"}
    </tbody>
  </table>
</div>

</body>
</html>"""
    return html_content, filename


def _get_report_extra(conn):
    """Fetch extra analytics data for the professional report."""
    port_names = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Alt",
        8443: "HTTPS-Alt", 6379: "Redis", 27017: "MongoDB",
    }
    extra = {}
    with conn.cursor() as cur:
        # Top attacking IPs
        cur.execute(
            "SELECT src_ip, COUNT(*) AS alert_count,"
            " MIN(COALESCE(severity, 4)) AS max_severity"
            " FROM events WHERE event_type = 'alert' AND src_ip IS NOT NULL"
            " GROUP BY src_ip ORDER BY alert_count DESC LIMIT 8"
        )
        extra["top_ips"] = cur.fetchall()

        # Top attack types
        cur.execute(
            "SELECT COALESCE(NULLIF(category,''), SUBSTRING_INDEX(signature,' ',3), 'Desconocido') AS attack_type,"
            " COUNT(*) AS count FROM events"
            " WHERE event_type = 'alert'"
            " GROUP BY attack_type ORDER BY count DESC LIMIT 8"
        )
        extra["top_attacks"] = cur.fetchall()

        # Top ports
        cur.execute(
            "SELECT dest_port, COUNT(*) AS count FROM events"
            " WHERE event_type = 'alert' AND dest_port IS NOT NULL AND dest_port > 0"
            " GROUP BY dest_port ORDER BY count DESC LIMIT 8"
        )
        extra["top_ports"] = cur.fetchall()

        # Open alerts count
        cur.execute(
            "SELECT COUNT(*) AS total FROM events e"
            " LEFT JOIN alert_status s ON s.event_id = e.id"
            " WHERE e.event_type='alert' AND COALESCE(s.status, 'nueva') = 'nueva'"
        )
        extra["open_alerts"] = cur.fetchone()["total"]

        # Open incidents count
        cur.execute("SELECT COUNT(*) AS total FROM incidents WHERE status != 'cerrado'")
        extra["open_incidents"] = cur.fetchone()["total"]

    return extra


@app.get("/api/reports/events.pdf")
@auth_required(min_role="admin")
def report_events_pdf():
    """Genera y descarga un informe PDF profesional de seguridad."""
    try:
        rows, summary, meta = _get_report_data(
            request.args.get("range", "24h"),
            request.args.get("from"),
            request.args.get("to"),
            request.args.get("limit") or 1000, # Limitado para evitar cuelgues
        )
        extra = _get_report_extra(db())
        html_content, _ = _build_report_html(rows, summary, meta, for_pdf=True, extra=extra)

        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        filename = "marshaall_report_{}.pdf".format(meta["now"].strftime("%Y%m%d_%H%M%S"))

        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename={}".format(filename),
                "Content-Type": "application/pdf",
                "Cache-Control": "no-cache" # Asegura la descarga limpia
            },
        )
    except Exception as e:
        log.error("Error generando reporte PDF: %s\n%s", e, traceback.format_exc())
        return jsonify({
            "error": "Error generando el reporte PDF",
            "detail": str(e),
        }), 500


@app.get("/api/reports/style.xsl")
def report_style_xsl():
    """Sirve la hoja de estilos XSLT para el reporte XML."""
    return Response(
        REPORT_XSLT,
        mimetype="application/xslt+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/reports/events.csv")
@auth_required(min_role="analista")
def report_events_csv():
    """Genera y descarga un CSV de eventos/alertas."""
    try:
        rows, summary, meta = _get_report_data(
            request.args.get("range", "24h"),
            request.args.get("from"),
            request.args.get("to"),
            request.args.get("limit"),
        )
        filename = "marshaall_report_{}.csv".format(meta["now"].strftime("%Y%m%d_%H%M%S"))

        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Fecha", "Tipo", "IP Origen", "IP Destino", "Protocolo",
                         "Puerto Origen", "Puerto Destino", "Firma", "Severidad", "Categoria"])
        # Prepare translation map
        attack_map = {
            "A Network Trojan was detected": "Troyano de red detectado",
            "Attempted Information Leak": "Intento de fuga de información",
            "Information Leak": "Fuga de información",
            "Network Trojan": "Troyano de red",
            "Misc activity": "Actividad diversa",
            "Misc Attack": "Ataque diverso",
            "Potentially Bad Traffic": "Tráfico potencialmente malicioso",
            "Bad Traffic": "Tráfico malicioso",
            "Web Application Attack": "Ataque a aplicación web",
            "Attempted Denial of Service": "Intento de denegación de servicio",
            "Denial of Service": "Denegación de servicio",
            "Detection of a Network Scan": "Escaneo de red detectado",
            "Network Scan": "Escaneo de red",
            "Attempted User Privilege Gain": "Intento de escalada de privilegios",
            "Attempted Administrator Privilege Gain": "Intento de acceso como administrador",
            "Successful Administrator Privilege Gain": "Acceso de administrador logrado",
            "Successful User Privilege Gain": "Escalada de privilegios lograda",
            "Decode of an RPC Query": "Decodificación de consulta RPC",
            "Executable Code was Detected": "Código ejecutable detectado",
            "A suspicious filename was detected": "Nombre de archivo sospechoso",
            "Not Suspicious Traffic": "Tráfico no sospechoso",
        }

        for ev in rows:
            sev_val = ev.get("severity", "")
            sev_label = {1: "Alta", 2: "Media", 3: "Baja"}.get(sev_val, str(sev_val) if sev_val else "")
            
            cat_name = ev.get("category", "") or ""
            for en, es in attack_map.items():
                if en.lower() in cat_name.lower():
                    cat_name = es
                    break
            
            writer.writerow([
                ev.get("id", ""),
                str(ev.get("ts", ""))[:19],
                ev.get("event_type", ""),
                ev.get("src_ip", "") or "",
                ev.get("dest_ip", "") or "",
                ev.get("proto", "") or "",
                ev.get("src_port", "") or "",
                ev.get("dest_port", "") or "",
                (ev.get("signature") or "")[:120],
                sev_label,
                cat_name,
            ])

        csv_content = output.getvalue()
        return Response(
            csv_content.encode("utf-8-sig"),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename={}".format(filename),
                "Content-Type": "text/csv; charset=utf-8",
            },
        )
    except Exception as e:
        log.error("Error generando reporte CSV: %s", e)
        return jsonify({"error": "Error generando el reporte CSV"}), 500


def ensure_admin_password():
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "admin1234")
    pwd_hash = generate_password_hash(admin_pass)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username=%s", (admin_user,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE users SET password_hash=%s, role='admin' WHERE username=%s", (pwd_hash, admin_user))
            else:
                cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,'admin')", (admin_user, pwd_hash))
    finally:
        conn.close()


for _attempt in range(10):
    try:
        ensure_admin_password()
        log.info("Admin seed completado")
        break
    except Exception as e:
        log.warning("BD no lista aun: %s", e)
        time.sleep(2)


# ===================================================================
# EMAIL TEST ENDPOINT
# ===================================================================

@app.get("/api/test-email")
@auth_required(min_role="admin")
def test_email():
    """Endpoint de prueba para verificar la configuración SMTP (solo admin)."""
    from emailer import send_email, is_smtp_configured

    if not is_smtp_configured():
        return jsonify({"error": "SMTP no configurado. Revise SMTP_HOST y SMTP_FROM en .env"}), 400

    to = REPORT_TO or ALERT_TO
    if not to:
        return jsonify({"error": "No hay destinatario configurado (REPORT_TO / ALERT_TO)"}), 400

    ok = send_email(
        to,
        "Marshaall — Email de Prueba",
        "<div style='font-family:system-ui,sans-serif;padding:24px;'>"
        "<h2 style='color:#1a2744;'>Marshaall — Test OK</h2>"
        "<p style='color:#374151;'>Si recibes este email, la configuración SMTP es correcta.</p>"
        "<p style='color:#6b7280;font-size:12px;'>Enviado el {}</p>"
        "</div>".format(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
    )
    if ok:
        return jsonify({"ok": True, "message": "Email de prueba enviado a {}".format(to)})
    else:
        return jsonify({"error": "Fallo al enviar email. Revise logs del backend y configuración SMTP."}), 500


# ===================================================================
# ALERT NOTIFICATION ENDPOINT (llamado por ingest)
# ===================================================================

_alert_lock = threading.Lock()
_alert_dedup = {}        # key: (signature, src_ip, dest_ip) -> timestamp último envío
_alert_minute = [0, 0.0] # [conteo_este_minuto, timestamp_inicio_minuto]


@app.post("/api/notify-alert")
def notify_alert_endpoint():
    """Recibe notificación de nueva alerta desde ingest y envía email."""
    # Autenticación por secreto interno
    secret = request.headers.get("X-Internal-Secret", "")
    if not INTERNAL_SECRET or not hmac.compare_digest(secret, INTERNAL_SECRET):
        return jsonify({"error": "No autorizado"}), 401

    data = request.get_json(force=True, silent=True) or {}

    to = ALERT_TO or REPORT_TO
    if not to:
        return jsonify({"ok": False, "reason": "no_recipient"}), 200

    now = time.time()
    sig_key = (
        data.get("signature", ""),
        data.get("src_ip", ""),
        data.get("dest_ip", ""),
    )

    with _alert_lock:
        # Rate limit global por minuto
        if now - _alert_minute[1] > 60:
            _alert_minute[0] = 0
            _alert_minute[1] = now
        if _alert_minute[0] >= ALERT_MAX_PER_MIN:
            log.info("Rate limit alcanzado (%d emails/min), alerta omitida", ALERT_MAX_PER_MIN)
            return jsonify({"ok": False, "reason": "rate_limited"}), 429

        # Deduplicación por (signature + src + dest) en ventana configurable
        last_sent = _alert_dedup.get(sig_key, 0)
        if now - last_sent < ALERT_DEDUP_WINDOW:
            log.debug("Alerta deduplicada: %s", sig_key)
            return jsonify({"ok": False, "reason": "deduplicated"}), 200

        _alert_dedup[sig_key] = now
        _alert_minute[0] += 1

    # Limpiar entradas antiguas del dedup (evitar memory leak)
    with _alert_lock:
        cutoff = now - ALERT_DEDUP_WINDOW * 2
        expired = [k for k, v in _alert_dedup.items() if v < cutoff]
        for k in expired:
            del _alert_dedup[k]

    try:
        from emailer import send_alert_email
        send_alert_email(to, data)
    except Exception as e:
        log.error("Error enviando email de alerta: %s", e)

    return jsonify({"ok": True})


# ===================================================================
# HELPER: generar reporte como bytes (para scheduler y email)
# ===================================================================

def generate_report_bytes(range_param="24h", fmt="pdf"):
    """
    Genera el reporte y devuelve (bytes, filename, mimetype).
    Intenta PDF; si falla, genera HTML.
    """
    conn = get_conn()
    try:
        range_map = {
            "1h": timedelta(hours=1), "6h": timedelta(hours=6),
            "24h": timedelta(hours=24), "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = range_map.get(range_param, timedelta(hours=24))
        now = datetime.now()
        ts_from = (now - delta).strftime("%Y-%m-%d %H:%M:%S")
        ts_to = now.strftime("%Y-%m-%d %H:%M:%S")
        log.info("generate_report_bytes range: %s -> %s", ts_from, ts_to)

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ts, event_type, src_ip, dest_ip, proto,"
                " signature, severity, flow_id, src_port, dest_port, category"
                " FROM events WHERE ts >= %s AND ts <= %s ORDER BY ts DESC LIMIT 5000",
                (ts_from, ts_to),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) AS total_events,"
                " SUM(CASE WHEN event_type='alert' THEN 1 ELSE 0 END) AS total_alerts,"
                " SUM(CASE WHEN severity=1 THEN 1 ELSE 0 END) AS sev_1,"
                " SUM(CASE WHEN severity=2 THEN 1 ELSE 0 END) AS sev_2,"
                " SUM(CASE WHEN severity=3 THEN 1 ELSE 0 END) AS sev_3,"
                " SUM(CASE WHEN severity IS NULL THEN 1 ELSE 0 END) AS sev_none"
                " FROM events WHERE ts >= %s AND ts <= %s",
                (ts_from, ts_to),
            )
            sr = cur.fetchone()

        summary = {
            "total_events": sr["total_events"] or 0,
            "total_alerts": sr["total_alerts"] or 0,
            "sev_1": sr["sev_1"] or 0, "sev_2": sr["sev_2"] or 0,
            "sev_3": sr["sev_3"] or 0, "sev_none": sr["sev_none"] or 0,
        }
        meta = {
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "range_from": ts_from, "range_to": ts_to,
            "total": len(rows), "now": now,
        }

        extra = _get_report_extra(conn)
        html_content, _ = _build_report_html(rows, summary, meta, for_pdf=True, extra=extra)

        if fmt == "pdf":
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=html_content).write_pdf()
                fn = "marshaall_report_{}.pdf".format(now.strftime("%Y%m%d_%H%M%S"))
                return pdf_bytes, fn, "application/pdf"
            except Exception as e:
                log.warning("PDF falló, usando HTML: %s", e)

        fn = "marshaall_report_{}.html".format(now.strftime("%Y%m%d_%H%M%S"))
        return html_content.encode("utf-8"), fn, "text/html"
    finally:
        conn.close()


# ===================================================================
# SCHEDULER DIARIO (APScheduler dentro del backend)
# ===================================================================
# Decisión: se corre dentro del backend con APScheduler en vez de un
# contenedor separado, porque:
# 1) Reutiliza el acceso a BD y las funciones de reporte ya existentes.
# 2) Gunicorn con 1 worker (default) evita duplicar jobs.
# 3) Simplifica la infraestructura Docker Compose sin añadir servicios.

_scheduler_started = False


def _start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    if not REPORT_TO:
        log.info("REPORT_TO no configurado — scheduler de reporte diario desactivado")
        return
    if not SMTP_HOST:
        log.info("SMTP_HOST no configurado — scheduler de reporte diario desactivado")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        hour, minute = REPORT_TIME.split(":")
        tz = pytz.timezone(REPORT_TZ)

        scheduler = BackgroundScheduler(timezone=tz)
        scheduler.add_job(
            _daily_report_job,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
            id="daily_report",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        _scheduler_started = True
        log.info(
            "Scheduler diario iniciado — reporte a las %s:%s (%s) para %s, rango=%s",
            hour, minute, REPORT_TZ, REPORT_TO, REPORT_RANGE,
        )
    except Exception as e:
        log.error("Error iniciando scheduler: %s\n%s", e, traceback.format_exc())


def _daily_report_job():
    """Job diario: genera reporte y lo envía por email."""
    log.info("Ejecutando reporte diario programado (rango=%s)...", REPORT_RANGE)
    try:
        report_bytes, filename, mimetype = generate_report_bytes(REPORT_RANGE, fmt="pdf")
        from emailer import send_report_email
        today_str = datetime.now(pytz.timezone(REPORT_TZ)).strftime("%Y-%m-%d")
        ok = send_report_email(REPORT_TO, today_str, report_bytes, filename, REPORT_RANGE)
        if ok:
            log.info("Reporte diario enviado a %s (%s)", REPORT_TO, filename)
        else:
            log.error("Fallo al enviar reporte diario a %s", REPORT_TO)
    except Exception as e:
        log.error("Error en job de reporte diario: %s\n%s", e, traceback.format_exc())


# Iniciar scheduler al cargar el módulo
_start_scheduler()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
