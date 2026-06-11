"""
Precipitation outlook from the NWS point forecast (via nws.py).

Combines the hourly probability of precipitation (chance + timing)
with the gridpoint forecast amounts (how much, and rain vs. snow).
Works inland and on the coast.
"""
import nws

DRY_THRESHOLD   = 20    # peak % below which a day reads as "dry"
WET_THRESHOLD   = 50    # peak % at/above which a day is flagged "wet"
SNOW_THRESHOLD  = 0.1   # inches of snow to call it snow
TRACE_THRESHOLD = 0.05  # inches below which precip is a trace


def _precip_type(amounts):
    """('rain' | 'snow' | 'rain/snow mix', amount_in) for a day's
    gridpoint totals."""
    rain = amounts.get('rain_in', 0.0)
    snow = amounts.get('snow_in', 0.0)
    if snow >= SNOW_THRESHOLD:
        # rain_in is liquid-equivalent; subtract the snow's melt to see
        # if there's meaningful liquid rain on top of the snow.
        liquid_rain = rain - snow / 10
        if liquid_rain > TRACE_THRESHOLD:
            return 'rain/snow mix', snow
        return 'snow', snow
    return 'rain', rain


def _amount_phrase(amounts):
    """Return (kind, phrase) for a day, e.g. ('rain', ', ~0.20 in
    expected'); the phrase is empty when the amount is only a trace."""
    kind, amount = _precip_type(amounts)
    if amount < TRACE_THRESHOLD:
        return kind, ''
    unit = 'in snow' if kind == 'snow' else 'in'
    return kind, f', ~{amount:.2f}{unit} expected'


def precip_summary(df, days):
    """Chance, type, amount, and timing of precip for each day."""
    if df.empty:
        return '  Precipitation data unavailable.\n\n'

    amounts_by_day = nws.precip_detail()
    content = ''
    for desc, day in days.items():
        day_df = df[df['local_date'] == day]
        if day_df.empty:
            content += f'{desc.upper()} precipitation data unavailable.\n\n'
            continue

        peak    = day_df.loc[day_df['pop'].idxmax()]
        max_pop = int(peak['pop'])
        kind, amount_phrase = _amount_phrase(amounts_by_day.get(day, {}))

        if max_pop < DRY_THRESHOLD:
            content += (f'{desc.upper()} looks dry, '
                        f'peak chance of precipitation only {max_pop}%.\n\n')
        else:
            content += (f'{desc.upper()} up to a {max_pop}% chance of {kind}'
                        f'{amount_phrase}, highest around {peak["local_time"]} '
                        f'({peak["short"].lower()}).\n\n')
    return content
