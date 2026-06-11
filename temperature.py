"""
Temperature outlook from the NWS point forecast (via nws.py).

Reads the hourly `temp_f` column and reports each day's high, low, and
the time it peaks. Works inland and on the coast.
"""


def temp_summary(df, days):
    """Daily high and low (°F) with the warmest time of day."""
    if df.empty:
        return '  Temperature data unavailable.\n\n'

    content = ''
    for desc, day in days.items():
        day_df = df[df['local_date'] == day]
        if day_df.empty:
            content += f'{desc.upper()} temperature data unavailable.\n\n'
            continue

        hi      = int(round(day_df['temp_f'].max()))
        lo      = int(round(day_df['temp_f'].min()))
        warmest = day_df.loc[day_df['temp_f'].idxmax()]
        content += (f'{desc.upper()} high {hi}°F, low {lo}°F '
                    f'(warmest around {warmest["local_time"]}).\n\n')
    return content
