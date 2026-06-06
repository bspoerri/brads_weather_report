"""
Surface wind from the NWS point forecast (via nws.py).

Sourced from the NWS rather than the GFS-Wave model so it is valid
inland as well as on the coast.
"""
from time_helpers import to_display_date


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


def wind_week_ahead(df):
    """Notably breezy and calm days over the forecast horizon."""
    if df.empty:
        return '💨 Wind\nWind outlook unavailable.\n'

    daily = df.groupby('local_date')['wind_kts'].mean()
    calm_days  = []
    windy_days = []
    for day, avg in daily.items():
        entry = {'date': day, 'avg': round(avg, 1)}
        if avg < 5:
            calm_days.append(entry)
        elif avg > 12:
            windy_days.append(entry)

    def format_days(days_list):
        return ''.join(
            f'  {to_display_date(d["date"])} | Avg Wind: {d["avg"]} kts\n'
            for d in days_list
        )

    content  = '💨 Wind\n'
    content += ('Calm Days:\n'  + format_days(calm_days)
                if calm_days  else 'No notably calm days ahead.\n')
    content += '\n'
    content += ('Breezy Days:\n' + format_days(windy_days)
                if windy_days else 'No notably breezy days ahead.\n')
    return content
