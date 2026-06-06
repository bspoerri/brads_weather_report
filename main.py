import os
import sys
from datetime import date

import localenv
localenv.load()  # populate os.environ from coastal.env before imports read it

import cache_location
import coast
import nws
import tide
import wave
import wind
import precipitation
import sunrise_sunset as sun
import quality
import display
import report_pdf
import emailer
from time_helpers import days_dict

REPORTS_DIR     = 'reports'
COORDS_CACHE    = 'my_coordinates.txt'


def resolve_location():
    """
    Seed the location cache. Priority: COASTAL_COORDS env (see
    coastal.env) -> existing cached coordinates -> IP geolocation.
    """
    coords = os.environ.get('COASTAL_COORDS')
    if coords:
        lat, lng = (float(x) for x in coords.split(','))
        cache_location.save_location(lat, lng)
    elif not os.path.exists(COORDS_CACHE):
        cache_location.save_location()  # IP geolocation fallback


def build_report():
    """
    Assemble the coastal report.

    Always reports wind, precipitation, and sunrise/sunset. Marine
    sections (tide, seas) are added only when near the coast, and the
    biotoxin section only in Maine.
    """
    next_two_days = days_dict('TODAY', 'TOMORROW')

    station_name, station_dist = coast.nearest_station()
    coastal  = coast.is_coastal()
    in_maine = coast.is_in_maine()

    nws_df = nws.hourly_forecast()

    report = display.print_greeting()
    if station_dist is not None:
        proximity = 'coastal' if coastal else 'inland'
        report += (f'Nearest tide station: {station_name} '
                   f'({station_dist:.0f} mi) -- {proximity}.\n')

    # ---- Marine forecast (coastal only): tide, wind, seas ----------
    if coastal:
        tide_df = tide.combine_tide_data()
        wave_df = wave.get_wave_forecast()
        have_waves = wave_df is not None and not wave_df.empty

        report += display.print_header('⛵ Marine Forecast')
        report += '\n📏 TIDES\n'
        report += (tide.tide_summary(tide_df, next_two_days)
                   if tide_df is not None else '  Tide data unavailable.\n\n')
        report += '💨 WIND\n'
        report += wind.wind_summary(nws_df, next_two_days)
        report += '🌊 SEAS\n'
        report += (wave.wave_summary(wave_df, next_two_days)
                   if have_waves else '  Seas data unavailable.\n\n')
    else:
        tide_df, wave_df, have_waves = None, None, False
        report += display.print_header('🌤️ Local Forecast')
        report += ('\n(Inland -- marine sections omitted: '
                   'more than 20 miles from the nearest tide station.)\n\n')
        report += '💨 WIND\n'
        report += wind.wind_summary(nws_df, next_two_days)

    # ---- Conditions (always): precipitation, sun ------------------
    report += display.print_header('🌤️ Conditions')
    report += '\n🌧️ PRECIPITATION\n'
    report += precipitation.precip_summary(nws_df, next_two_days)
    report += '🌅 SUNRISE & SUNSET\n'
    report += sun.sun_summary(next_two_days)

    # ---- Water quality (Maine only): biotoxin closures ------------
    if in_maine:
        report += display.print_header('🦪 Water Quality')
        report += '\n' + quality.quality_summary()

    # ---- Week ahead outlook ---------------------------------------
    report += display.print_header('📅 Week Ahead Outlook') + '\n'
    report += wind.wind_week_ahead(nws_df) + '\n'
    report += precipitation.precip_week_ahead(nws_df) + '\n'
    if have_waves:
        report += wave.wave_week_ahead(wave_df) + '\n'
    if tide_df is not None:
        report += tide.tide_week_ahead(tide_df)

    return report


def main():
    resolve_location()
    report = build_report()
    print(report)

    pdf_path = os.path.join(REPORTS_DIR, f'coastal_report_{date.today():%Y%m%d}.pdf')
    report_pdf.save_pdf(report, pdf_path)
    print(f'\nSaved PDF: {os.path.abspath(pdf_path)}')

    # Email the PDF to the distro list only when asked (run_daily.sh and
    # the scheduled job pass --email); a bare `python main.py` won't send.
    if '--email' in sys.argv:
        emailer.send_pdf(
            pdf_path,
            subject=f'Coastal Report — {date.today():%A %m/%d/%Y}',
        )


if __name__ == '__main__':
    main()
