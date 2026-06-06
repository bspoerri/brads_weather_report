"""
Sea-state forecast from the NOAA/NWS GFS-Wave model (NOMADS GRIB2).

Wind is no longer derived here -- it comes from the NWS point forecast
in wind.py so it works inland as well -- so this module covers waves
only: height, period, and direction.
"""
import os
import check_location
import pygrib
import pandas as pd
import numpy as np
import api_endpoint as api
from datetime import datetime, timezone
from time_helpers import (
    time_dict, to_local_time, to_datestring, to_12hr, to_display_date
)

CWD = os.getcwd()
NOMADS_FILTER = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfswave.pl'
WAVE_GRIDS = {
    'atlocn': {
        'file': 'gfswave.t{cycle}z.atlocn.0p16.f{fhour}.grib2',
        'lat_range': (0, 80),
        'lon_range': (-100, 30),
        'resolution': 0.16,
    },
    'wcoast': {
        'file': 'gfswave.t{cycle}z.wcoast.0p16.f{fhour}.grib2',
        'lat_range': (15, 65),
        'lon_range': (-180, -100),
        'resolution': 0.16,
    },
    'epacif': {
        'file': 'gfswave.t{cycle}z.epacif.0p16.f{fhour}.grib2',
        'lat_range': (-20, 60),
        'lon_range': (-180, -70),
        'resolution': 0.16,
    },
    'arctic': {
        'file': 'gfswave.t{cycle}z.arctic.9km.f{fhour}.grib2',
        'lat_range': (60, 90),
        'lon_range': (-180, 180),
        'resolution': 0.08,
    },
}

UNIT_CONVERSIONS  = {'swh': ('ft', lambda v: v * 3.28084)}
DIRECTION_UNITS   = {'dirpw', 'swdir', 'wvdir'}
SHORT_NAME_LABELS = {
    'swh'   : 'Wave Height',
    'perpw' : 'Peak Period',
    'dirpw' : 'Peak Direction',
}


def select_grid(cycle: str, forecast_hour: str):
    """
    Selects the highest-resolution wave grid file template that
    covers the current location, falling back to the global grid
    if no match is found.
    Returns:
        grid_link (str): GRIB2 filename for the selected grid.
    """
    lat, lng = check_location.get_coordinates()
    candidates = [
        details for details in WAVE_GRIDS.values()
        if (details['lat_range'][0] <= lat <= details['lat_range'][1]
            and details['lon_range'][0] <= lng <= details['lon_range'][1])
    ]
    candidates.sort(key=lambda x: x['resolution'])
    if candidates:
        return (candidates[0]['file']
                .replace('{cycle}', cycle)
                .replace('{fhour}', forecast_hour))
    return f'gfswave.t{cycle}z.global.0p25.f{forecast_hour}.grib2'


def get_latest_cycle():
    """
    Most recent GFS-Wave run that should be published, as
    (cycle_date '%Y%m%d', cycle_hour '00'/'06'/'12'/'18'). A ~6-hour
    lag accounts for model run + upload time on NOMADS.
    """
    lagged   = datetime.now(timezone.utc).hour - 6
    cycle_dt = (time_dict['TODAY'] if lagged >= 0
                else time_dict['YESTERDAY'])
    cycle    = ('18' if lagged >= 18 else
                '12' if lagged >= 12 else
                '06' if lagged >= 6  else
                '00')
    return cycle_dt, cycle


def deg_to_compass(deg):
    """Convert a bearing in degrees to a 16-point compass label."""
    dirs = [
        'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
    ]
    return dirs[round(deg / 22.5) % 16]


def get_wave_forecast():
    """
    Download the GFS-Wave GRIB2 files for the next 7 days (every 12 h),
    sample the grid point nearest the location, and return a tidy
    DataFrame of wave height / period / direction with local and UTC
    timestamps. GRIB files are deleted after parsing. Returns an empty
    DataFrame if nothing could be downloaded.
    """
    lat, lng         = check_location.get_coordinates()
    cycle_dt, cycle  = get_latest_cycle()
    forecast_periods = [f'{h:03d}' for h in range(0, 169, 12)]
    grib_paths       = []

    for period in forecast_periods:
        params = {
            'file'      : select_grid(cycle, period),
            'var_HTSGW' : 'on',
            'var_PERPW' : 'on',
            'var_DIRPW' : 'on',
            'subregion' : '',
            'leftlon'   : lng - 2,
            'rightlon'  : lng + 2,
            'toplat'    : lat + 2,
            'bottomlat' : lat - 2,
            'dir'       : f'/gfs.{cycle_dt}/{cycle}/wave/gridded',
        }
        grib_path = f'{CWD}/gribs/wave_forecast_{period}.grib2'
        grib_paths.append(grib_path)
        api.save_grib_request(NOMADS_FILTER, grib_path, params=params)

    records = []
    for path, period in zip(grib_paths, forecast_periods):
        if not os.path.exists(path):
            continue
        grbs = pygrib.open(path)
        for grb in grbs:
            lat_arr, lng_arr = grb.latlons()
            lng_arr_norm     = np.where(lng_arr > 180, lng_arr - 360, lng_arr)
            dist             = np.sqrt(
                (lat_arr - lat)**2 + (lng_arr_norm - lng)**2
            )
            dist[np.ma.getmaskarray(grb.values)] = np.inf
            idx = np.unravel_index(dist.argmin(), dist.shape)
            records.append({
                'date'          : cycle_dt,
                'cycle'         : cycle,
                'forecast_hour' : period,
                'short_name'    : grb.shortName,
                'value'         : grb.values[idx],
                'units'         : grb.units,
                'grid_lat'      : lat_arr[idx],
                'grid_lng'      : (lng_arr[idx] - 360
                                   if lng_arr[idx] > 180
                                   else lng_arr[idx]),
            })
        grbs.close()

    for path in grib_paths:
        if os.path.exists(path):
            os.remove(path)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    for short, (unit, fn) in UNIT_CONVERSIONS.items():
        mask = df['short_name'] == short
        df.loc[mask, 'value'] = fn(df.loc[mask, 'value'])
        df.loc[mask, 'units'] = unit
    df.loc[df['short_name'].isin(DIRECTION_UNITS), 'units'] = 'Degree true'

    df['cycle_start'] = pd.to_datetime(
        df['date'] + df['cycle'], format='%Y%m%d%H'
    )
    df['utc_forecast_time'] = (
        df['cycle_start']
        + pd.to_timedelta(df['forecast_hour'].astype(int), unit='h')
    )
    local_dt         = to_local_time(df['utc_forecast_time'])
    df['local_date'] = to_datestring(local_dt)
    df['local_time'] = to_12hr(local_dt.dt.strftime('%H:%M'))
    df['short_name'] = df['short_name'].map(SHORT_NAME_LABELS)
    df.insert(
        df.columns.get_loc('units'),
        'dir',
        df.apply(
            lambda row: deg_to_compass(row['value'])
            if row['short_name'] == 'Peak Direction'
            else np.nan,
            axis=1
        )
    )
    return df.drop(columns=['cycle_start', 'date', 'utc_forecast_time'])


def wave_summary(df, days):
    """Peak and smallest seas for each day in `days`, with the wave
    height, peak period, and direction at those times."""
    content     = ''
    wave_df     = df[df['short_name'].isin(
        ['Wave Height', 'Peak Period', 'Peak Direction']
    )]
    height_df   = wave_df[wave_df['short_name'] == 'Wave Height'].set_index('local_time')
    period_df   = wave_df[wave_df['short_name'] == 'Peak Period'].set_index('local_time')
    wave_dir_df = wave_df[wave_df['short_name'] == 'Peak Direction'].set_index('local_time')

    for desc, day in days.items():
        height   = height_df[height_df['local_date'] == day]
        period   = period_df[period_df['local_date'] == day]
        wave_dir = wave_dir_df[wave_dir_df['local_date'] == day]

        if height.empty:
            content += f'{desc.upper()} seas data unavailable.\n\n'
            continue

        avg_height = height['value'].mean()
        wave_desc  = ('glassy'   if avg_height <= 1 else
                      'small'    if avg_height <= 3 else
                      'moderate' if avg_height <= 6 else
                      'large'    if avg_height <= 9 else
                      'massive')

        peak_time     = height['value'].idxmax()
        min_time      = height['value'].idxmin()
        peak_height   = round(height.loc[peak_time,  'value'], 1)
        min_height    = round(height.loc[min_time,   'value'], 1)
        peak_period   = round(period.loc[peak_time,  'value'], 0)
        min_period    = round(period.loc[min_time,   'value'], 0)
        peak_wave_dir = wave_dir.loc[peak_time, 'dir']
        min_wave_dir  = wave_dir.loc[min_time,  'dir']

        content = (content
                   + f'{desc.upper()} seas will be {wave_desc}, '
                   + f'peaking around {peak_height} ft '
                   + f'out of the {peak_wave_dir} '
                   + f'at {peak_period}s periods around {peak_time}.\n'
                   + f'Smallest waves around {min_height} ft '
                   + f'out of the {min_wave_dir} '
                   + f'at {min_period}s periods around {min_time}.\n\n')
    return content


def wave_week_ahead(df):
    """Classify each day of the forecast as calm (<2 ft avg) or rough
    (>6 ft avg) seas, by daily mean wave height."""
    height_df    = df[df['short_name'] == 'Wave Height']
    daily_height = height_df.groupby('local_date')['value'].mean()

    calm_days  = []
    rough_days = []
    for day, avg_height in daily_height.items():
        entry = {'date': day, 'avg_height': round(avg_height, 1)}
        if avg_height < 2:
            calm_days.append(entry)
        elif avg_height > 6:
            rough_days.append(entry)

    def format_days(days_list):
        return ''.join(
            f'  {to_display_date(d["date"])} | Avg Seas: {d["avg_height"]} ft\n'
            for d in days_list
        )

    content  = '🌊 Seas\n'
    content += ('Calm Days:\n'  + format_days(calm_days)
                if calm_days  else 'No notably calm seas ahead.\n')
    content += '\n'
    content += ('Rough Days:\n' + format_days(rough_days)
                if rough_days else 'No notably rough seas ahead.\n')
    return content
