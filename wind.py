"""
Surface wind from the NWS point forecast (via nws.py).

Sourced from the NWS rather than the GFS-Wave model so it is valid
inland as well as on the coast.
"""


def _speed_phrase(row):
    """'X kts out of the DIR', or 'calm' when there's no wind."""
    kts = round(row['wind_kts'])
    direction = (row['wind_dir'] or '').strip()
    if kts == 0 or not direction:
        return 'calm'
    return f'{kts} kts out of the {direction}'


def wind_summary(df, days):
    """Peak / lightest wind for each requested day."""
    if df.empty:
        return '  Wind data unavailable.\n\n'

    content = ''
    for desc, day in days.items():
        day_df = df[df['local_date'] == day]
        if day_df.empty:
            content += f'{desc.upper()} wind data unavailable.\n\n'
            continue

        avg       = day_df['wind_kts'].mean()
        wind_desc = ('little or light' if avg <= 5  else
                     'moderate'        if avg <= 10 else
                     'stiff'           if avg <= 15 else
                     "frigging blowin' out theyah guy")

        peak = day_df.loc[day_df['wind_kts'].idxmax()]
        low  = day_df.loc[day_df['wind_kts'].idxmin()]

        content = (content
                   + f'{desc.upper()} breeze will be {wind_desc}, '
                   + f'peaking {_speed_phrase(peak)} at {peak["local_time"]}.\n'
                   + f'Lightest winds {_speed_phrase(low)} '
                   + f'at {low["local_time"]}.\n\n')
    return content
