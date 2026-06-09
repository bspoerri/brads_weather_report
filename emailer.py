"""
Email the report PDF over SMTP.

Sends through a plain SMTP server (Gmail by default), so the job has no
GUI dependency and runs reliably unattended -- e.g. from the 5am launchd
agent while the Mac is asleep/locked and no one is logged in. (The old
implementation drove Mail.app via AppleScript, which timed out under
launchd; see git history.)

Configuration comes from coastal.env (see coastal.env.example):

    COASTAL_SENDER          From: address (also the default SMTP login)
    COASTAL_SMTP_PASSWORD   SMTP password -- for Gmail, an App Password
                            (https://myaccount.google.com/apppasswords),
                            NOT your normal account password
    COASTAL_SMTP_HOST       SMTP server   (default: smtp.gmail.com)
    COASTAL_SMTP_PORT       SMTP port     (default: 587, STARTTLS; 465 = SSL)
    COASTAL_SMTP_USER       SMTP login    (default: COASTAL_SENDER)
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

# Resolved at send time from COASTAL_SENDER (see coastal.env); the
# placeholder keeps any personal address out of committed source.
PLACEHOLDER_SENDER = 'you@example.com'
RECIPIENTS_FILE    = 'recipients.txt'

DEFAULT_SMTP_HOST  = 'smtp.gmail.com'
DEFAULT_SMTP_PORT  = 587


def load_recipients(path=RECIPIENTS_FILE):
    """Addresses from the distro list, skipping blanks and # comments."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [line.strip() for line in f
                if line.strip() and not line.lstrip().startswith('#')]


def _build_message(pdf_abs, recipients, sender, subject, body):
    """Compose an EmailMessage with the PDF attached."""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = sender
    msg['To']      = ', '.join(recipients)
    msg.set_content(body)

    with open(pdf_abs, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf',
                           filename=os.path.basename(pdf_abs))
    return msg


def send_pdf(pdf_path, recipients=None, sender=None,
             subject='Coastal Report', body=None, test=False):
    """
    Email `pdf_path` to `recipients` (defaults to the distro list),
    sent from `sender` (defaults to COASTAL_SENDER). Returns True on
    success.

    When `test` is True the message goes only to the sender, bypassing
    the distro list -- handy for verifying a send without notifying
    everyone.
    """
    sender = sender or os.environ.get('COASTAL_SENDER', PLACEHOLDER_SENDER)
    if test:
        recipients = [sender]
    elif recipients is None:
        recipients = load_recipients()
    if not recipients:
        print('Email: no recipients in the distro list; skipping send.')
        return False
    if not os.path.exists(pdf_path):
        print(f'Email: PDF not found ({pdf_path}); skipping send.')
        return False

    host     = os.environ.get('COASTAL_SMTP_HOST', DEFAULT_SMTP_HOST)
    port     = int(os.environ.get('COASTAL_SMTP_PORT', DEFAULT_SMTP_PORT))
    user     = os.environ.get('COASTAL_SMTP_USER', sender)
    password = os.environ.get('COASTAL_SMTP_PASSWORD')
    if not password:
        print('Email: COASTAL_SMTP_PASSWORD is not set; skipping send. '
              '(For Gmail, create an App Password and add it to coastal.env.)')
        return False

    body = body or 'Your coastal report is attached.'
    msg  = _build_message(os.path.abspath(pdf_path), recipients,
                          sender, subject, body)

    try:
        context = ssl.create_default_context()
        # Port 465 speaks TLS from the start (SMTPS); everything else
        # (e.g. 587) connects in the clear and upgrades via STARTTLS.
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=60) as s:
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=60) as s:
                s.starttls(context=context)
                s.login(user, password)
                s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        print(f'Email: send failed: {e}')
        return False
    print(f'Email: sent to {", ".join(recipients)} (from {sender}).')
    return True
