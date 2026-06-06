"""
Load personal, gitignored configuration from `coastal.env` into the
process environment so it never has to live in committed source.

Format is simple `KEY=value` lines (blank lines and `#` comments are
ignored). Real environment variables take precedence, so anything
already exported is left untouched.

See coastal.env.example for the available keys.
"""
import os

LOCAL_ENV_FILE = 'coastal.env'


def load(filename=LOCAL_ENV_FILE):
    """Parse the local env file (if present) and set each KEY=value in
    os.environ without overriding variables already set."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)
