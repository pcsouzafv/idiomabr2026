from types import SimpleNamespace

import pytest

from app.services import email_service


def _settings(**overrides):
    data = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "smtp_user": "admin@example.com",
        "smtp_password": "secret",
        "smtp_from": "admin@example.com",
        "smtp_ssl": True,
        "smtp_tls": False,
        "support_email": "support@example.com",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_is_smtp_configured_requires_basics(monkeypatch):
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings())
    assert email_service.is_smtp_configured() is True

    monkeypatch.setattr(email_service, "get_settings", lambda: _settings(smtp_host=""))
    assert email_service.is_smtp_configured() is False

    monkeypatch.setattr(email_service, "get_settings", lambda: _settings(smtp_from=""))
    assert email_service.is_smtp_configured() is False


def test_is_smtp_configured_requires_password_when_user_present(monkeypatch):
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings(smtp_password=""))
    assert email_service.is_smtp_configured() is False

    monkeypatch.setattr(
        email_service,
        "get_settings",
        lambda: _settings(smtp_user="", smtp_password=""),
    )
    assert email_service.is_smtp_configured() is True


def test_send_email_raises_when_not_configured(monkeypatch):
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings(smtp_host=""))
    with pytest.raises(ValueError, match="SMTP not configured"):
        email_service.send_email(
            to_email="student@example.com",
            subject="Teste",
            html_body="<p>oi</p>",
            text_body="oi",
        )


def test_support_contact_uses_support_email_and_reply_to(monkeypatch):
    calls = []
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings())

    def _fake_send_email(to_email, subject, html_body, text_body=None, reply_to=None):
        calls.append(
            {
                "to_email": to_email,
                "subject": subject,
                "reply_to": reply_to,
                "text_body": text_body,
            }
        )

    monkeypatch.setattr(email_service, "send_email", _fake_send_email)

    email_service.send_support_message_to_team(
        student_name="Aluno",
        student_email="aluno@example.com",
        student_phone="+55 11 99999-9999",
        subject="Nao consigo entrar",
        message="Preciso de ajuda para fazer login.",
        category="acesso",
        context_url="/login",
    )

    assert calls
    assert calls[0]["to_email"] == "support@example.com"
    assert calls[0]["reply_to"] == "aluno@example.com"


def test_send_email_verification_email_uses_expected_subject(monkeypatch):
    calls = []
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings())

    def _fake_send_email(to_email, subject, html_body, text_body=None, reply_to=None):
        calls.append(
            {
                "to_email": to_email,
                "subject": subject,
                "html_body": html_body,
                "text_body": text_body,
                "reply_to": reply_to,
            }
        )

    monkeypatch.setattr(email_service, "send_email", _fake_send_email)

    email_service.send_email_verification_email(
        to_email="student@example.com",
        verify_url="https://app.example.com/verify-email?token=abc",
    )

    assert calls
    assert calls[0]["to_email"] == "student@example.com"
    assert calls[0]["subject"] == "Confirme seu email - IdiomasBR"
    assert "verify-email?token=abc" in (calls[0]["text_body"] or "")
