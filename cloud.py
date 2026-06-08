"""
Cloud cover outlook from the NWS gridpoint forecast (via nws.py).

The gridpoint 'skyCover' field gives cloud cover as a percentage over
the forecast horizon. We average it per day and translate it into a
plain-language sky description. Works inland and on the coast.
"""
from time_helpers import to_display_date


def _sky_label(pct):
    """Plain-language sky condition for a cloud-cover percentage,
    following the standard clear/few/scattered/broken/overcast bands."""
    if pct <= 5:
        return 'clear'
    if pct <= 25:
        return 'mostly clear'
    if pct <= 50:
        return 'partly cloudy'
    if pct <= 87:
        return 'mostly cloudy'
    return 'overcast'


def cloud_summary(df, days):
    """Average cloud cover, a sky description, and the clearest time of
    day for each requested day."""
    if df.empty:
        return '  Cloud cover data unavailable.\n\n'

    content = ''
    for desc, day in days.items():
        day_df = df[df['local_date'] == day]
        if day_df.empty:
            content += f'{desc.upper()} cloud cover data unavailable.\n\n'
            continue

        avg      = int(round(day_df['sky_pct'].mean()))
        clearest = day_df.loc[day_df['sky_pct'].idxmin()]
        content += (f'{desc.upper()} {_sky_label(avg)}, averaging {avg}% cloud '
                    f'cover (clearest around {clearest["local_time"]} at '
                    f'{int(clearest["sky_pct"])}%).\n\n')
    return content


def cloud_week_ahead(df):
    """Average cloud cover per day over the forecast horizon."""
    if df.empty:
        return '☁️ Cloud Cover\nCloud cover outlook unavailable.\n'

    daily   = df.groupby('local_date')['sky_pct'].mean()
    content = '☁️ Cloud Cover\n'
    for day, pct in daily.items():
        avg = int(round(pct))
        content += (f'  {to_display_date(day)} | {avg}% cloud cover '
                    f'({_sky_label(avg)})\n')
    return content
