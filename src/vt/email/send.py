"""Envío por Gmail SMTP (contraseña de aplicación). Sin credenciales no envía: lo dice y devuelve False."""
import os
import smtplib
from email.message import EmailMessage
from ..config import load


def build_message(sender, to, subject, html, text):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, ", ".join(to), subject
    m.set_content(text or " ")
    m.add_alternative(html, subtype="html")
    return m


def send(subject, html, text, to, dry_run=False):
    cfg = load("email")
    sender = os.environ.get("GMAIL_USER") or cfg["sender"]
    pwd = os.environ.get("GMAIL_APP_PASSWORD")
    msg = build_message(sender, to, subject, html, text)
    if dry_run or not pwd:
        print(f"[email NO enviado: {'dry-run' if dry_run else 'sin GMAIL_APP_PASSWORD'}] asunto: {subject} -> {len(to)} destinatarios")
        return False
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(sender, pwd)
        s.send_message(msg)
    print(f"[email enviado] asunto: {subject}")
    return True
