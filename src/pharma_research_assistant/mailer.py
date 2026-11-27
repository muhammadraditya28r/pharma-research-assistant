import smtplib
from email.message import EmailMessage

from .digest import email_html


def send_digest(
    sender: str,
    app_password: str,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    message.add_alternative(email_html(body), subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(sender, app_password)
        server.send_message(message)
