"""
Consolidated week-ahead outlook.

Rather than a per-metric dump, this collects what's *notable* about each
day across wind, temperature, precipitation, cloud cover, seas, and
extreme tides, and emits one chronological line per standout day. Quiet
days are omitted, and calm/quiet conditions aren't flagged -- a
highlights digest is about what stands out.

Marine inputs (wave_df, tide_df) are None inland and are skipped then.
All sources key on the same '%Y%m%d' date string, so they merge directly.
"""
import nws
import precipitation
from time_helpers import to_display_date, time_dict

# Notability thresholds.
WINDY_KTS     = 12     # daily mean wind at/above which a day reads "breezy"
HOT_F         = 85     # daily high at/above which a day reads "hot"
FREEZING_F    = 32     # daily low at/below which a night reads "freezing"
CLEAR_PCT     = 25     # daily avg cloud cover at/below -> "clear skies"
OVERCAST_PCT  = 80     # daily avg cloud cover at/above -> "overcast"
STARGAZE_PCT  = 20     # evening cloud cover at/below -> good for stargazing
EVENING_HOUR  = 20     # local hour from which cloud cover counts as "evening"
ROUGH_SEAS_FT = 6      # daily mean wave height above which seas read "rough"


def week_ahead_digest(nws_df, cloud_df, wave_df, tide_df):
    """One chronological highlights list -- a line per standout day across
    wind, temperature, precip, cloud, seas, and extreme tides."""
    flags = {}

    def add(day, phrase):
        flags.setdefault(day, []).append(phrase)

    # ---- Wind, temperature, precipitation (hourly NWS frame) ----------
    if not nws_df.empty:
        for day, avg in nws_df.groupby('local_date')['wind_kts'].mean().items():
            if avg > WINDY_KTS:
                add(day, f'breezy ({round(avg)} kts)')

        for day, hi in nws_df.groupby('local_date')['temp_f'].max().items():
            if hi >= HOT_F:
                add(day, f'hot — high {int(round(hi))}°F')
        for day, lo in nws_df.groupby('local_date')['temp_f'].min().items():
            if lo <= FREEZING_F:
                add(day, f'freezing — low {int(round(lo))}°F')

        amounts = nws.precip_detail()
        for day, pop in nws_df.groupby('local_date')['pop'].max().items():
            if pop >= precipitation.WET_THRESHOLD:
                kind, phrase = precipitation._amount_phrase(amounts.get(day, {}))
                add(day, f'{int(pop)}% chance of {kind}{phrase}')

    # ---- Cloud cover, plus clear evenings for stargazing --------------
    if not cloud_df.empty:
        for day, avg in cloud_df.groupby('local_date')['sky_pct'].mean().items():
            if avg <= CLEAR_PCT:
                add(day, 'clear skies')
            elif avg >= OVERCAST_PCT:
                add(day, 'overcast')

        evening = cloud_df[cloud_df['hour'] >= EVENING_HOUR]
        for day, avg in evening.groupby('local_date')['sky_pct'].mean().items():
            if avg <= STARGAZE_PCT:
                add(day, '🔭 great stargazing night')

    # ---- Seas (coastal only) ------------------------------------------
    if wave_df is not None and not wave_df.empty:
        height_df = wave_df[wave_df['short_name'] == 'Wave Height']
        for day, avg in height_df.groupby('local_date')['value'].mean().items():
            if avg > ROUGH_SEAS_FT:
                add(day, f'rough seas ({round(avg, 1)} ft)')

    # ---- Extreme tides (coastal only) ---------------------------------
    if tide_df is not None:
        extremes = tide_df[tide_df['outlier'].isin([1, -1])]
        for i in extremes.index:
            label = ('very high tide' if extremes.loc[i, 'outlier'] == 1
                     else 'very low tide')
            add(extremes.loc[i, 'date'],
                f'{label} {extremes.loc[i, "12hr_time"]} '
                f'({extremes.loc[i, "tide_ft"]:.1f} ft)')

    # ---- Assemble -----------------------------------------------------
    # Today and tomorrow are already covered in detail by the main
    # report, so the outlook starts the day after tomorrow.
    skip = {time_dict['TODAY'], time_dict['TOMORROW']}
    days = [day for day in sorted(flags) if day not in skip]
    if not days:
        return 'A quiet week ahead — nothing notable in the forecast.\n'

    lines = [f'  {to_display_date(day)} | ' + '; '.join(flags[day])
             for day in days]
    return '\n\n'.join(lines) + '\n'
