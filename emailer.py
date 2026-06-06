"""
Email the report PDF through the macOS Mail.app via AppleScript.

Uses the already-configured Mail account, so there are no SMTP
credentials to store. The sending account (COASTAL_SENDER) must exist
in Mail > Settings > Accounts. The first send may trigger a one-time
"control Mail.app" automation permission prompt.
"""
import os
import subprocess

# Resolved at send time from COASTAL_SENDER (see coastal.env); the
# placeholder keeps any personal address out of committed source.
PLACEHOLDER_SENDER = 'you@example.com'
RECIPIENTS_FILE    = 'recipients.txt'


def load_recipients(path=RECIPIENTS_FILE):
    """Addresses from the distro list, skipping blanks and # comments."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [line.strip() for line in f
                if line.strip() and not line.lstrip().startswith('#')]


def _esc(s):
    """Escape a value for embedding in an AppleScript string literal."""
    return str(s).replace('\\', '\\\\').replace('"', '\\"')


def _build_script(pdf_abs, recipients, sender, subject, body):
    """Compose the AppleScript that creates an outgoing Mail message
    with the PDF attached and sends it to every recipient."""
    lines = [
        'tell application "Mail"',
        ('  set newMessage to make new outgoing message with properties '
         '{subject:"%s", content:"%s", visible:false}'
         % (_esc(subject), _esc(body))),
        '  tell newMessage',
        '    set sender to "%s"' % _esc(sender),
    ]
    for r in recipients:
        lines.append('    make new to recipient at end of to recipients '
                     'with properties {address:"%s"}' % _esc(r))
    # A short delay lets Mail finish attaching before the message is sent
    # (a well-known AppleScript/Mail timing quirk).
    lines += [
        '    make new attachment with properties '
        '{file name:(POSIX file "%s")} at after the last paragraph'
        % _esc(pdf_abs),
        '  end tell',
        '  delay 2',
        '  send newMessage',
        'end tell',
    ]
    return '\n'.join(lines)


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

    body = body or 'Your coastal report is attached.'
    script = _build_script(os.path.abspath(pdf_path), recipients,
                           sender, subject, body)
    try:
        subprocess.run(['osascript', '-e', script],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f'Email: send failed: {e.stderr.strip() or e}')
        return False
    print(f'Email: sent to {", ".join(recipients)} (from {sender}).')
    return True
