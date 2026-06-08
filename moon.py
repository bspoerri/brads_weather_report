"""
Current lunar phase, computed locally from the moon's synodic age.

Like sunrise_sunset, this is computed rather than fetched so the report
carries no extra API dependency. It tracks the moon's age since a known
new moon against the mean synodic month -- accurate to within a few
hours, which is plenty for naming the phase and its illumination.
"""
import math
from datetime import datetime, timedelta, timezone
from time_helpers import LOCAL_TZ

SYNODIC_MONTH  = 29.530588853    # mean days between successive new moons
# A reference new moon (2000-01-06 18:14 UTC) to count cycles from.
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

# The eight named phases with their emoji, in synodic order from new moon.
PHASES = [
    ('New Moon',        '🌑'),
    ('Waxing Crescent', '🌒'),
    ('First Quarter',   '🌓'),
    ('Waxing Gibbous',  '🌔'),
    ('Full Moon',       '🌕'),
    ('Waning Gibbous',  '🌖'),
    ('Last Quarter',    '🌗'),
    ('Waning Crescent', '🌘'),
]


def moon_age(when=None):
    """Age of the moon in days for `when` (default now, UTC): 0 at new
    moon, ~14.8 at full, wrapping at the synodic month."""
    when = when or datetime.now(timezone.utc)
    elapsed = (when - KNOWN_NEW_MOON).total_seconds() / 86400.0
    return elapsed % SYNODIC_MONTH


def phase_name(age):
    """(name, emoji) for a moon age, snapped to the nearest of the eight
    named phases."""
    idx = int((age / SYNODIC_MONTH) * 8 + 0.5) % 8
    return PHASES[idx]


def illumination(age):
    """Fraction of the moon's disc lit (0 at new, 1 at full) for an
    age in days."""
    return (1 - math.cos(2 * math.pi * age / SYNODIC_MONTH)) / 2


def moon_summary(when=None):
    """Current phase, illumination, and the next full and new moons."""
    when = when or datetime.now(timezone.utc)
    age  = moon_age(when)
    name, emoji = phase_name(age)
    illum = round(illumination(age) * 100)

    # Days until the age next reaches new (0) and full (half a cycle).
    half      = SYNODIC_MONTH / 2
    next_new  = when + timedelta(days=SYNODIC_MONTH - age)
    next_full = when + timedelta(days=(half - age) % SYNODIC_MONTH)

    return (f'  {emoji} {name}\n'
            f'  Illumination | {illum}%\n'
            f'  Moon age     | {age:.1f} days\n'
            f'  Next full    | {next_full.astimezone(LOCAL_TZ):%a %m/%d}\n'
            f'  Next new     | {next_new.astimezone(LOCAL_TZ):%a %m/%d}\n\n')
