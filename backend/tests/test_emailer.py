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


@patch("emailer.smtplib.SMTP")
def test_send_alert_email_sev2(mock_smtp_class):
    from emailer import send_alert_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    alert = {
        "severity": 2,
        "signature": "Tráfico sospechoso HTTP",
        "src_ip": "10.0.0.1",
        "dest_ip": "10.0.0.2",
        "category": "Suspicious",
        "ts": "2026-02-28T12:00:00",
        "event_id": 10002,
    }

    result = send_alert_email("admin@test.com", alert)
    assert result is True


@patch("emailer.smtplib.SMTP")
def test_send_alert_email_sev3(mock_smtp_class):
    from emailer import send_alert_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    alert = {
        "severity": 3,
        "signature": "Consulta DNS inusual",
        "src_ip": "10.0.0.5",
        "dest_ip": "8.8.8.8",
        "category": "DNS",
        "ts": "2026-02-28T12:00:00",
        "event_id": 10003,
    }

    result = send_alert_email("admin@test.com", alert)
    assert result is True


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
    assert "reporte.pdf" in msg_str


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


# ------------------------------------------------------------------
# get_smtp_config
# ------------------------------------------------------------------

def test_get_smtp_config():
    from emailer import get_smtp_config
    cfg = get_smtp_config()
    assert cfg["host"] == "smtp.test.com"
    assert cfg["port"] == 587
    assert cfg["user"] == "test@test.com"
    assert cfg["from_addr"] == "marshaall@test.com"
    assert cfg["use_tls"] is True


@patch("emailer.smtplib.SMTP")
def test_send_email_no_tls(mock_smtp_class, monkeypatch):
    monkeypatch.setenv("SMTP_TLS", "false")
    from emailer import send_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    result = send_email("dest@test.com", "Test", "<p>Hola</p>")

    assert result is True
    mock_server.starttls.assert_not_called()


@patch("emailer.smtplib.SMTP")
def test_send_email_no_auth(mock_smtp_class, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASS", "")
    from emailer import send_email
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    result = send_email("dest@test.com", "Test", "<p>Hola</p>")

    assert result is True
    mock_server.login.assert_not_called()
