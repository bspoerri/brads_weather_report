"""
Shared access to the NWS (api.weather.gov) point forecast.

Both wind.py and precipitation.py read from the same hourly forecast,
and coast.py needs the point's state, so the network calls are made
once here and cached for the rest of the run.
"""
import api_endpoint as api
import pandas as pd
import check_location
from time_helpers import to_datestring, to_12hr, to_local_time

NWS_API    = 'https://api.weather.gov'
MPH_TO_KTS = 0.868976
MM_TO_IN   = 1 / 25.4

_points  = None
_hourly  = None
_precip  = None
_grid    = None
_sky     = None

HOURLY_COLUMNS = [
    'local_date', 'local_time', 'pop', 'short',
    'wind_kts', 'wind_dir', 'temp_f',
]

SKY_COLUMNS = ['local_date', 'local_time', 'hour', 'sky_pct']


def _get_points():
    """Cached `/points` metadata properties (grid, forecast URLs,
    relativeLocation). Returns {} on failure."""
    global _points
    if _points is None:
        lat, lng = check_location.get_coordinates()
        data = api.get_json_request(f'{NWS_API}/points/{lat:.4f},{lng:.4f}')
        _points = data['properties'] if data else {}
    return _points


def _relative_location():
    """NWS 'relativeLocation' properties (nearest city/state), or {}."""
    return _get_points().get('relativeLocation', {}).get('properties', {})


def state():
    """Two-letter state code for the cached coordinates (e.g. 'ME'),
    or None if unavailable."""
    return _relative_location().get('state')


def location_name():
    """Nearest place as 'City, ST', or None if unavailable."""
    rel = _relative_location()
    city, st = rel.get('city'), rel.get('state')
    return f'{city}, {st}' if city and st else None


def hourly_forecast():
    """
    Cleaned NWS hourly forecast as a DataFrame, one row per hour:
        local_date  '%Y%m%d'
        local_time  12-hour clock
        pop         probability of precipitation (%)
        short       short sky/weather description
        wind_kts    sustained wind speed (knots)
        wind_dir    wind direction (compass)
        temp_f      temperature (degrees F)

    Returns an empty DataFrame if the forecast can't be retrieved.
    """
    global _hourly
    if _hourly is not None:
        return _hourly

    url  = _get_points().get('forecastHourly')
    data = api.get_json_request(url) if url else None
    if not data or 'properties' not in data:
        _hourly = pd.DataFrame(columns=HOURLY_COLUMNS)
        return _hourly

    df = pd.DataFrame(data['properties']['periods'])
    # NWS startTime is ISO 8601 with a local UTC offset, so it is
    # already local once parsed.
    start = pd.to_datetime(df['startTime'])
    df['local_date'] = to_datestring(start)
    df['local_time'] = to_12hr(start.dt.strftime('%H:%M'))
    df['pop'] = (
        df['probabilityOfPrecipitation']
        .apply(lambda x: x.get('value') if isinstance(x, dict) else x)
        .fillna(0)
        .astype(float)
    )
    df['short']    = df['shortForecast']
    df['wind_kts'] = (
        df['windSpeed'].str.extract(r'(\d+)').astype(float)[0] * MPH_TO_KTS
    )
    df['wind_dir'] = df['windDirection']
    df['temp_f']   = df['temperature'].astype(float)

    _hourly = df[HOURLY_COLUMNS].copy()
    return _hourly


def _get_grid_data():
    """Cached `/gridpoints` forecast properties (precip, sky cover,
    etc.). Returns {} on failure. Shared so precip and cloud cover make
    a single network call."""
    global _grid
    if _grid is None:
        url  = _get_points().get('forecastGridData')
        data = api.get_json_request(url) if url else None
        _grid = data['properties'] if (data and 'properties' in data) else {}
    return _grid


def _sum_by_local_day(values):
    """
    Aggregate an NWS gridpoint time-series (list of
    {'validTime': '<ISO>/<duration>', 'value': mm}) into inches per
    local date. The value is attributed to the interval's start day.
    """
    daily = {}
    if not values:
        return daily
    starts = pd.to_datetime([v['validTime'].split('/')[0] for v in values],
                            utc=True)
    local_dates = to_datestring(to_local_time(pd.Series(starts)))
    for date, v in zip(local_dates, values):
        if v.get('value') is not None:
            daily[date] = daily.get(date, 0.0) + v['value'] * MM_TO_IN
    return daily


def precip_detail():
    """
    Per-day precipitation amounts (inches) from the NWS gridpoint
    forecast, keyed by local '%Y%m%d' date:
        {date: {'rain_in': float, 'snow_in': float}}
    Returns {} if the gridpoint forecast can't be retrieved.
    """
    global _precip
    if _precip is not None:
        return _precip

    props = _get_grid_data()
    if not props:
        _precip = {}
        return _precip

    rain  = _sum_by_local_day(props.get('quantitativePrecipitation', {}).get('values'))
    snow  = _sum_by_local_day(props.get('snowfallAmount', {}).get('values'))

    _precip = {
        date: {'rain_in': rain.get(date, 0.0), 'snow_in': snow.get(date, 0.0)}
        for date in set(rain) | set(snow)
    }
    return _precip


def sky_cover():
    """
    NWS gridpoint sky cover (cloud cover) as a DataFrame, one row per
    forecast interval:
        local_date  '%Y%m%d'
        local_time  12-hour clock
        sky_pct     cloud cover (%)

    Returns an empty DataFrame if the gridpoint forecast can't be
    retrieved.
    """
    global _sky
    if _sky is not None:
        return _sky

    props  = _get_grid_data()
    values = props.get('skyCover', {}).get('values') if props else None
    if not values:
        _sky = pd.DataFrame(columns=SKY_COLUMNS)
        return _sky

    # gridpoint validTime is '<ISO UTC>/<duration>'; attribute each
    # interval to its start time, converted to local.
    starts = pd.to_datetime([v['validTime'].split('/')[0] for v in values],
                            utc=True)
    local  = to_local_time(pd.Series(starts))
    df = pd.DataFrame({
        'local_date': to_datestring(local),
        'local_time': to_12hr(local.dt.strftime('%H:%M')),
        'hour':       local.dt.hour,
        'sky_pct':    [v.get('value') for v in values],
    }).dropna(subset=['sky_pct'])
    df['sky_pct'] = df['sky_pct'].astype(float)

    _sky = df[SKY_COLUMNS].copy()
    return _sky
