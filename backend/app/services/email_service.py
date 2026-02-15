import html
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import get_settings


def _clean_header(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip()


def is_smtp_configured() -> bool:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        return False
    if settings.smtp_user and not settings.smtp_password:
        return False
    return True


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> None:
    settings = get_settings()
    if not is_smtp_configured():
        raise ValueError("SMTP not configured")

    msg = EmailMessage()
    msg["From"] = _clean_header(settings.smtp_from)
    msg["To"] = _clean_header(to_email)
    msg["Subject"] = _clean_header(subject)
    if reply_to:
        msg["Reply-To"] = _clean_header(reply_to)
    msg.set_content(text_body or "Use a HTML-capable email client to view this message.")
    msg.add_alternative(html_body, subtype="html")

    if settings.smtp_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    subject = "Redefinicao de senha - IdiomasBR"
    safe_url = html.escape(reset_url, quote=True)
    text_body = f"Use este link para redefinir sua senha: {reset_url}"
    html_body = (
        "<p>Voce solicitou a redefinicao de senha.</p>"
        f"<p><a href=\"{safe_url}\">Clique aqui para redefinir a senha</a></p>"
        "<p>Se voce nao solicitou, ignore este email.</p>"
    )
    send_email(to_email, subject, html_body, text_body)


def send_email_verification_email(to_email: str, verify_url: str) -> None:
    subject = "Confirme seu email - IdiomasBR"
    safe_url = html.escape(verify_url, quote=True)
    text_body = f"Confirme seu email acessando este link: {verify_url}"
    html_body = (
        "<p>Bem-vindo ao IdiomasBR.</p>"
        f"<p><a href=\"{safe_url}\">Clique aqui para confirmar seu email</a></p>"
        "<p>Se voce nao criou esta conta, ignore este email.</p>"
    )
    send_email(to_email, subject, html_body, text_body)


def _support_email_target() -> str:
    settings = get_settings()
    support_email = (settings.support_email or settings.smtp_from).strip()
    if not support_email:
        raise ValueError("Support email not configured")
    return support_email


def send_support_message_to_team(
    student_name: str,
    student_email: str,
    student_phone: Optional[str],
    subject: str,
    message: str,
    category: Optional[str] = None,
    context_url: Optional[str] = None,
) -> None:
    safe_name = html.escape(student_name or "-", quote=True)
    safe_email = html.escape(student_email or "-", quote=True)
    safe_phone = html.escape(student_phone or "-", quote=True)
    safe_subject = html.escape(subject, quote=True)
    safe_category = html.escape(category or "geral", quote=True)
    safe_context = html.escape(context_url or "-", quote=True)
    safe_message = html.escape(message, quote=True).replace("\n", "<br>")

    email_subject = f"[Suporte IdiomasBR] {subject}"
    text_body = (
        "Nova mensagem de suporte.\n"
        f"Aluno: {student_name}\n"
        f"Email: {student_email}\n"
        f"Telefone: {student_phone or '-'}\n"
        f"Categoria: {category or 'geral'}\n"
        f"Contexto: {context_url or '-'}\n\n"
        f"Assunto: {subject}\n\n"
        f"{message}"
    )
    html_body = (
        "<p>Nova mensagem de suporte recebida.</p>"
        "<ul>"
        f"<li><strong>Aluno:</strong> {safe_name}</li>"
        f"<li><strong>Email:</strong> {safe_email}</li>"
        f"<li><strong>Telefone:</strong> {safe_phone}</li>"
        f"<li><strong>Categoria:</strong> {safe_category}</li>"
        f"<li><strong>Contexto:</strong> {safe_context}</li>"
        "</ul>"
        f"<p><strong>Assunto:</strong> {safe_subject}</p>"
        f"<p>{safe_message}</p>"
    )
    send_email(
        _support_email_target(),
        email_subject,
        html_body,
        text_body,
        reply_to=student_email,
    )


def send_support_acknowledgement(student_email: str, student_name: str, subject: str) -> None:
    support_email = _support_email_target()
    safe_name = html.escape(student_name or "aluno", quote=True)
    safe_subject = html.escape(subject, quote=True)

    text_body = (
        f"Ola, {student_name or 'aluno'}!\n\n"
        "Recebemos sua mensagem de suporte e responderemos o quanto antes.\n"
        f"Assunto recebido: {subject}\n\n"
        "Equipe IdiomasBR"
    )
    html_body = (
        f"<p>Ola, {safe_name}!</p>"
        "<p>Recebemos sua mensagem de suporte e responderemos o quanto antes.</p>"
        f"<p><strong>Assunto recebido:</strong> {safe_subject}</p>"
        "<p>Equipe IdiomasBR</p>"
    )
    send_email(
        student_email,
        "Recebemos sua solicitacao - Suporte IdiomasBR",
        html_body,
        text_body,
        reply_to=support_email,
    )


def send_support_email_to_student(
    to_email: str,
    subject: str,
    message: str,
    sent_by: str,
    reply_to: Optional[str] = None,
) -> None:
    safe_message = html.escape(message, quote=True).replace("\n", "<br>")
    safe_sender = html.escape(sent_by, quote=True)
    html_body = (
        f"<p>{safe_message}</p>"
        "<p>Se precisar de ajuda adicional, responda este email.</p>"
        f"<p><strong>Equipe de Suporte:</strong> {safe_sender}</p>"
    )
    text_body = (
        f"{message}\n\n"
        "Se precisar de ajuda adicional, responda este email.\n"
        f"Equipe de Suporte: {sent_by}"
    )
    send_email(
        to_email,
        subject,
        html_body,
        text_body,
        reply_to=reply_to or _support_email_target(),
    )
