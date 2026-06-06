"""
Tide forecast from NOAA CO-OPS (Tides & Currents).

Finds the nearest tide station, pulls this week's high/low predictions,
and flags unusually high/low tides by comparing them against the past
year of observed high/low extremes.
"""
import check_location
import datetime as dt
import pandas as pd
import numpy as np
import api_endpoint as api
from time_helpers import time_dict, to_12hr, to_display_date

STATIONS_URL = ('https://api.tidesandcurrents.noaa.gov'
                '/mdapi/prod/webapi/stations.json')
TIDE_DATA_URL = ('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter')

TIDE_API_DEFAULTS = {
    'datum'     : 'MLLW',
    'format'    : 'json',
    'units'     : 'english',
    'time_zone' : 'lst_ldt',
}


_stations_cache = None


def get_tide_stations():
    """
    DataFrame of NOAA tide-prediction stations (id index; name, lat,
    lng), or None if the request fails.

    Cached: both the coast-proximity check and the tide forecast need
    this list, but it only needs fetching once per run.
    """
    global _stations_cache
    if _stations_cache is not None:
        return _stations_cache
    response = api.get_json_request(STATIONS_URL)
    if response is None:
        return None
    station_dict = {
        station['id']: {
            'name': f'{station["name"]}, {station["state"]}',
            'lat' : float(station['lat']),
            'lng' : float(station['lng']),
        }
        for station in response['stations']
        if station['tidal'] and station['forecast']
    }
    stations_df = pd.DataFrame.from_dict(station_dict, orient='index')
    stations_df.index.name = 'id'
    _stations_cache = stations_df
    return stations_df


def clean_tide_df(df):
    """Normalize the raw CO-OPS columns: split the timestamp into
    'date' ('%Y%m%d') and '12hr_time', and rename value/type fields."""
    if 't' in df.columns:
        df['t'] = pd.to_datetime(df['t'])
        # '%Y%m%d' to match days_dict() and the wind/wave date columns.
        df.insert(0, 'date', df['t'].dt.strftime('%Y%m%d'))
        df.insert(1, '12hr_time', df['t'].dt.strftime('%H:%M'))
        df.rename(columns={'t': 'date_time'}, inplace=True)
    if 'v' in df.columns:
        df.rename(columns={'v': 'tide_ft'}, inplace=True)
        df['tide_ft'] = df['tide_ft'].astype('float64')
    if 'ty' in df.columns:
        df.rename(columns={'ty': 'type'}, inplace=True)
    return df


def get_weekly_hilo_prediction(station: str):
    """High/low tide predictions for a station from today through the
    end of the week, or None on failure."""
    params = {
        **TIDE_API_DEFAULTS,
        'station'    : station,
        'product'    : 'predictions',
        'begin_date' : time_dict['TODAY'],
        'end_date'   : time_dict['EOW'],
        'interval'   : 'hilo',
    }
    data = api.get_json_request(TIDE_DATA_URL, params)
    if data is None:
        return None
    if 'predictions' not in data:
        print('Semantic error:', data['error']['message'])
        return None
    return clean_tide_df(pd.DataFrame(data['predictions']))


def get_hist_hilo(station: str):
    """Past year of observed high/low tides for a station (used to set
    the outlier thresholds), or None on failure."""
    params = {
        **TIDE_API_DEFAULTS,
        'station'    : station,
        'product'    : 'high_low',
        'begin_date' : time_dict['T_MINUS_365'],
        'end_date'   : time_dict['YESTERDAY'],
    }
    data = api.get_json_request(TIDE_DATA_URL, params)
    if data is None:
        return None
    if 'data' not in data:
        print('Semantic error:', data['error']['message'])
        return None
    return clean_tide_df(pd.DataFrame(data['data']))


def flag_outlier_tides(predictions_df, hist_hilos,
                       low_band=0.05, high_band=0.95):
    """
    Add an 'outlier' column to the predictions: +1 if a high tide
    exceeds the historical `high_band` quantile, -1 if a low tide falls
    below the `low_band` quantile, else NaN. Thresholds are computed
    separately for highs and lows from the historical extremes.
    """
    hist_hilos['adj_type'] = hist_hilos['type'].str[0]
    tide_bounds = (
        hist_hilos.groupby('adj_type')['tide_ft']
        .agg(lower=lambda x: x.quantile(low_band),
             upper=lambda x: x.quantile(high_band))
    )
    adj_type = predictions_df['type'].str[0]
    lower    = adj_type.map(tide_bounds['lower'])
    upper    = adj_type.map(tide_bounds['upper'])
    predictions_df['outlier'] = np.select(
        [predictions_df['tide_ft'] < lower,
         predictions_df['tide_ft'] > upper],
        [-1, 1],
        default=np.nan
    )
    return predictions_df


def combine_tide_data():
    """
    End-to-end tide pipeline: nearest station -> weekly predictions ->
    outlier flags from a year of history -> 12-hour time strings.
    Returns the prediction DataFrame, or None if any step fails.
    """
    stations = get_tide_stations()
    if stations is None:
        return None
    my_station  = check_location.find_nearest(stations)
    predictions = get_weekly_hilo_prediction(my_station)
    if predictions is None:
        return None
    historical  = get_hist_hilo(my_station)
    if historical is None:
        return None
    predictions = flag_outlier_tides(predictions, historical)
    predictions['12hr_time'] = to_12hr(predictions['12hr_time'])
    return predictions


def tide_summary(df, days):
    """Time-to-next-tide plus the high/low tide times for each day in
    `days`, marking any outlier tides as VERY HIGH / VERY LOW."""
    next_tide  = df[df['date_time'] >= dt.datetime.now()].iloc[0]
    until_next = (
        (next_tide['date_time'] - dt.datetime.now()).total_seconds() / 3600
    )
    content = (
        'The next tide will be '
        f'{"HIGH" if next_tide["type"] == "H" else "LOW"} '
        f'in {until_next:.1f} hours.\n\n'
    )

    for desc, day in days.items():
        day_df = df[df['date'] == day]
        highs  = []
        lows   = []

        for i in day_df.index:
            prefix = ''
            if day_df.loc[i, 'outlier'] == -1:
                prefix = '(--VERY LOW--) '
            elif day_df.loc[i, 'outlier'] == 1:
                prefix = '(--VERY HIGH--) '
            entry = f'{prefix}{day_df.loc[i, "12hr_time"]}'
            if day_df.loc[i, 'type'] == 'H':
                highs.append(entry)
            else:
                lows.append(entry)

        content = (content
                   + f'{desc.title()}\n'
                   + f'  High Tides | {" & ".join(highs)}\n'
                   + f'  Low Tides  | {" & ".join(lows)}\n\n')
    return content


def tide_week_ahead(df):
    """List only the outlier (very high / very low) tides over the
    coming week, with date, time, and height."""
    content  = '📏 Extreme Tides (week ahead):\n'
    extremes = df[df['outlier'].isin([1, -1])]

    if extremes.empty:
        return content + 'No extreme tides in the week ahead.\n'

    for record in extremes.index:
        label   = ('VERY HIGH' if extremes.loc[record, 'outlier'] == 1
                   else 'VERY LOW')
        content = (content
                   + '  '
                   + f'{to_display_date(extremes.loc[record, "date"])} '
                   + f'{extremes.loc[record, "12hr_time"]} | '
                   + f'{extremes.loc[record, "tide_ft"]:.1f} ft | '
                   + label + '\n')
    return content