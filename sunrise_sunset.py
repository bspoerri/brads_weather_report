"""
Sunrise and sunset, computed locally with the NOAA solar position
algorithm (the math behind the NOAA Global Monitoring Lab solar
calculator). Computing it avoids depending on a third-party
astronomy API for a report that needs to run reliably.
"""
import math
from datetime import datetime, timedelta, timezone
import check_location
from time_helpers import LOCAL_TZ

J2000        = 2451545.0                  # Julian date of 2000-01-01 12:00 UTC
OBLIQUITY    = math.radians(23.4397)      # Earth's axial tilt
SUN_ALTITUDE = math.radians(-0.833)       # geometric sunrise/sunset altitude


def _julian_day_number(d):
    """Integer Julian Day Number (noon-based) for a calendar date."""
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    return (d.day + (153 * m + 2) // 5 + 365 * y
            + y // 4 - y // 100 + y // 400 - 32045)


def _jd_to_local(jd):
    """Convert a Julian date (UTC) to a local-time datetime."""
    utc = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=jd - J2000)
    return utc.astimezone(LOCAL_TZ)


def sun_events(d, lat, lng):
    """
    Sunrise and sunset (local datetimes) for date `d` at lat/lng.
    Returns (sunrise, sunset), with either None during polar
    day/night when the sun does not cross the horizon.
    """
    n      = _julian_day_number(d) - J2000 + 0.0008
    J_star = n - lng / 360.0                      # mean solar time
    M      = math.radians((357.5291 + 0.98560028 * J_star) % 360)
    C      = (1.9148 * math.sin(M)
              + 0.0200 * math.sin(2 * M)
              + 0.0003 * math.sin(3 * M))          # equation of center
    lam    = math.radians((math.degrees(M) + C + 282.9372) % 360)
    J_transit = (J2000 + J_star
                 + 0.0053 * math.sin(M)
                 - 0.0069 * math.sin(2 * lam))      # solar noon
    decl   = math.asin(math.sin(lam) * math.sin(OBLIQUITY))

    lat_r   = math.radians(lat)
    cos_w0  = ((math.sin(SUN_ALTITUDE) - math.sin(lat_r) * math.sin(decl))
               / (math.cos(lat_r) * math.cos(decl)))
    if cos_w0 > 1:    # sun stays below the horizon all day
        return None, None
    if cos_w0 < -1:   # sun stays above the horizon all day
        return None, None

    w0 = math.degrees(math.acos(cos_w0)) / 360.0
    return _jd_to_local(J_transit - w0), _jd_to_local(J_transit + w0)


def sun_summary(days):
    """Sunrise, sunset, and daylight length for each requested day."""
    lat, lng = check_location.get_coordinates()
    content  = ''
    for desc, day in days.items():
        d = datetime.strptime(day, '%Y%m%d').date()
        sunrise, sunset = sun_events(d, lat, lng)

        if sunrise is None or sunset is None:
            content += f'{desc.title()}\n  No sunrise/sunset (polar day or night).\n\n'
            continue

        daylight = sunset - sunrise
        hours, rem = divmod(int(daylight.total_seconds()), 3600)
        minutes = rem // 60
        content += (f'{desc.title()}\n'
                    f'  Sunrise  | {sunrise.strftime("%I:%M %p")}\n'
                    f'  Sunset   | {sunset.strftime("%I:%M %p")}\n'
                    f'  Daylight | {hours}h {minutes}m\n\n')
    return content
