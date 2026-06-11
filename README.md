# Brad's Coastal Report ☕

A daily, location-aware coastal weather report for the Gulf of Maine (and
anywhere else, with graceful degradation). It pulls live data from NOAA /
NWS and Maine state sources, prints a clean terminal report, saves it as a
PDF, and can email it to a distribution list every morning.

```
⛵ Marine Forecast      📏 tides · 💨 wind · 🌊 seas (next two days)
🌤️ Conditions          🌡️ temperature · 🌧️ precipitation (chance, amount, rain/snow) · ☁️ cloud cover · 🌅 sunrise & sunset · 🌙 moon phase
🦪 Water Quality        biotoxin / red-tide closures (Maine only)
📅 Week Ahead Highlights  one line per standout day — heat, storms, clear nights for stargazing, rough seas, extreme tides
```

## What it reports

- **Tides** — high/low predictions for today & tomorrow, plus extreme
  ("very high/low") tides in the week ahead, flagged against a year of
  history.
- **Wind** — peak and lightest wind per day, with direction.
- **Seas** — wave height, period, and direction.
- **Temperature** — daily high and low, with the warmest time of day.
- **Precipitation** — chance, expected amount, and **rain vs. snow** type.
- **Cloud cover** — average cloud cover and a plain-language sky
  description (clear → overcast) per day, with the clearest time of day.
- **Sunrise / sunset** — with daylight length.
- **Moon phase** — current phase and illumination, plus the next full
  and new moons.
- **Water quality** — active shellfish biotoxin (red-tide) closures at and
  near your location.
- **Week ahead** — a consolidated highlights digest: one line per standout
  day over the forecast horizon, flagging only what's notable (breezy, hot
  or freezing, wet, clear or overcast, clear nights for stargazing, rough
  seas, and extreme tides). Quiet days are omitted.

### Location gating

- **Marine sections (tides, seas)** are shown only when you're within
  **20 miles of a NOAA tide station**. Inland, the report still gives wind,
  temperature, precipitation, cloud cover, sunrise/sunset, and moon phase.
- **Water quality** is shown only when the location is **in Maine** (NOAA's
  national HAB system doesn't cover the Gulf of Maine).

## Data sources

| Section | Source |
|---|---|
| Tides | NOAA CO-OPS Tides & Currents API |
| Wind / temperature / precipitation / cloud cover | National Weather Service (`api.weather.gov`) |
| Seas | NOAA/NWS GFS-Wave model (NOMADS GRIB2) |
| Sunrise / sunset | NOAA solar position algorithm (computed locally) |
| Moon phase | Synodic-month calculation (computed locally) |
| Biotoxin closures | Maine Dept. of Marine Resources public ArcGIS service |

All sources are keyless — no API tokens required.

## Requirements

- **macOS** (PDF rendering uses AppKit; scheduling uses launchd). Emailing
  is provider-agnostic SMTP, so it works headless/unattended.
- **Python 3.12** with: `requests`, `pandas`, `numpy`, `pygrib`, `pyobjc`
  (the `weather_env` conda environment has these)

## Setup

```bash
# 1. Configure your personal settings (gitignored)
cp coastal.env.example coastal.env
#   then edit coastal.env:
#     COASTAL_COORDS=43.7965,-70.2489     your lat,lng
#     COASTAL_SENDER=you@gmail.com        address to send from
#     COASTAL_SMTP_PASSWORD=...           SMTP/Gmail App Password
#     COASTAL_CONTACT=app (you@gmail.com) NWS User-Agent contact

# 2. (Optional) set up the email distribution list
./recipients.sh add someone@example.com
./recipients.sh list
```

`coastal.env`, `recipients.txt`, and `my_coordinates.txt` are all gitignored
— your personal info never enters the repo.

## Usage

```bash
python main.py            # print the report + save a PDF to reports/
python main.py --email    # also email the PDF to the distro list
python main.py --test     # email only the sender (trial run, skips the distro list)
./run_daily.sh            # wrapper used by the scheduler (runs with --email)
```

PDFs are written to `reports/coastal_report_YYYYMMDD.pdf`, rendered with a
monospaced font and full-color emoji via macOS AppKit (falls back to
`cupsfilter` if AppKit is unavailable).

### Email

Sending uses **SMTP** (Gmail by default), so it has no GUI dependency and
runs reliably from the unattended 5am scheduler. Configure in `coastal.env`:

- `COASTAL_SENDER` — the From: address (also the default SMTP login).
- `COASTAL_SMTP_PASSWORD` — for Gmail, an **App Password**
  (https://myaccount.google.com/apppasswords), *not* your normal password.
- `COASTAL_SMTP_HOST` / `COASTAL_SMTP_PORT` — default to `smtp.gmail.com:587`
  (STARTTLS; use `465` for SSL). Override for another provider.
- `COASTAL_SMTP_USER` — optional; defaults to `COASTAL_SENDER`.

Manage recipients with `./recipients.sh add|remove|list <email>`.

### Schedule it daily at 5 AM

```bash
./schedule_daily.sh           # install a launchd agent (runs daily at 05:00)
./schedule_daily.sh remove    # uninstall
```

The agent runs `run_daily.sh` (which passes `--email`), logging to `logs/`.
Email goes out over SMTP, so it sends even while the Mac is asleep/locked.
(The color-emoji PDF rendering still uses AppKit, which works best in your
logged-in session.)

## Project structure

```
main.py             entry point: assembles the report, saves PDF, emails
localenv.py         loads coastal.env into the environment
coast.py            coastal (20 mi) and Maine gating
nws.py              NWS point forecast (wind, precip, state) — cached
tide.py             NOAA tide stations, predictions, extremes
wave.py             GFS-Wave seas (downloads + parses GRIB2)
wind.py             wind summary / outlook (from NWS)
precipitation.py    precip chance, amount, rain/snow (from NWS)
sunrise_sunset.py   NOAA solar calculator
quality.py          Maine DMR biotoxin closures
api_endpoint.py     HTTP helper (JSON + GRIB), default User-Agent
time_helpers.py     date/time formatting + local timezone
display.py          greeting and section headers
report_pdf.py       text -> PDF (AppKit, cupsfilter fallback)
emailer.py          email the PDF via SMTP
cache_location.py   write the coordinate cache
check_location.py   read the coordinate cache; nearest-station search
recipients.sh       manage the email distribution list
run_daily.sh        run wrapper for the scheduler
schedule_daily.sh   install/remove the daily launchd job
coastal.env.example template for personal config
```

## Notes

- Default location resolves in this order: `COASTAL_COORDS` →
  cached `my_coordinates.txt` → IP geolocation.
- The GFS-Wave step downloads ~15 GRIB files, so a coastal run takes a
  minute or two; inland runs skip it and are fast.
- Timezone handling is DST-aware (resolves the IANA zone), so dates across a
  daylight-saving boundary stay correct.

## Author Comments

This project started as a project without LLM assistance. However, after getting the practice I wanted to (APIs and various packages) out of the exercise, I decided to refine and secure the finished product with Claude.

