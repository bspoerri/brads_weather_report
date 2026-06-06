"""
Shared date/time utilities used across the report modules.

Provides the local timezone (DST-aware), a table of common date stamps
(today, tomorrow, end-of-week, etc.), and helpers to convert between
the various string/Series time formats the data sources return.
"""
import os
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _local_zone():
    """
    Best-effort IANA local timezone so conversions stay DST-correct
    year-round. A captured fixed offset (e.g. -04:00) would be wrong
    for dates on the other side of a daylight-saving boundary.
    """
    try:
        key = os.readlink('/etc/localtime').split('zoneinfo/')[-1]
        return ZoneInfo(key)
    except (OSError, ValueError, ZoneInfoNotFoundError):
        return datetime.now().astimezone().tzinfo


LOCAL_TZ = _local_zone()
_TODAY   = date.today()

# Date stamps ('%Y%m%d') used to build API query ranges and to match
# the date columns in the forecast frames.
time_dict = {
    'T_MINUS_365': (_TODAY - timedelta(days=365)).strftime('%Y%m%d'),
    'YESTERDAY':   (_TODAY - timedelta(days=1)).strftime('%Y%m%d'),
    'TODAY':       _TODAY.strftime('%Y%m%d'),
    'TOMORROW':    (_TODAY + timedelta(days=1)).strftime('%Y%m%d'),
    'EOW':         (_TODAY + timedelta(days=7)).strftime('%Y%m%d'),
}


def days_dict(*keys):
    """
    Build a label -> date string dict for use in summary functions.
    Keys must match time_dict entries.

    Usage:
        days_dict('TODAY', 'TOMORROW')
        -> {'today': '20260606', 'tomorrow': '20260607'}
    """
    return {k.lower(): time_dict[k] for k in keys}


def to_12hr(time_to_convert):
    """Format a time as 12-hour 'HH:MM AM/PM'. Accepts a pandas Series
    of '%H:%M' strings or a single datetime-like object."""
    if isinstance(time_to_convert, pd.Series):
        new_time = pd.to_datetime(time_to_convert, format='%H:%M')
        return new_time.dt.strftime('%I:%M %p')
    return time_to_convert.strftime('%I:%M %p')


def to_datestring(date_to_convert):
    """Format a date as '%Y%m%d'. Accepts a pandas Series (tz-aware or
    naive) or a single date/datetime object."""
    if isinstance(date_to_convert, pd.Series):
        if pd.api.types.is_datetime64tz_dtype(date_to_convert):
            return date_to_convert.dt.strftime('%Y%m%d')
        return pd.to_datetime(date_to_convert).dt.strftime('%Y%m%d')
    return date_to_convert.strftime('%Y%m%d')


def to_local_time(time_to_convert, ref_zone: str = 'UTC'):
    """Convert a time (Series or scalar) to LOCAL_TZ. Naive inputs are
    assumed to be in `ref_zone` (UTC by default) before converting."""
    ref_tz = ZoneInfo(ref_zone)
    if isinstance(time_to_convert, pd.Series):
        converted = pd.to_datetime(time_to_convert)
        if converted.dt.tz is None:
            converted = converted.dt.tz_localize(ref_tz)
        return converted.dt.tz_convert(LOCAL_TZ)
    converted = pd.to_datetime(time_to_convert)
    if converted.tzinfo is None:
        converted = converted.tz_localize(ref_tz)
    return converted.tz_convert(LOCAL_TZ)


def to_display_date(date_str: str, fmt: str = '%A %m/%d'):
    """
    Convert a '%Y%m%d' date string to a display format.
    Defaults to 'Saturday 06/06'.

    Usage:
        to_display_date('20260606')         -> 'Saturday 06/06'
        to_display_date('20260606', '%b %d') -> 'Jun 06'
    """
    return datetime.strptime(date_str, '%Y%m%d').strftime(fmt)
