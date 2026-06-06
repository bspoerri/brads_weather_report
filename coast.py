"""
Location gating for the report.

Marine sections (tide, seas) only run when the coordinates are near
the coast; the biotoxin section only runs in Maine.
"""
import numpy as np
import check_location
import tide
import nws

EARTH_RADIUS_MI    = 3958.8
COAST_THRESHOLD_MI = 20


def haversine_mi(lat1, lng1, lat2, lng2):
    """Great-circle distance in statute miles. Any argument may be a
    NumPy array for vectorized distance to many points."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MI * np.arcsin(np.sqrt(a))


def nearest_station():
    """
    (name, distance_mi) of the nearest NOAA tide station to the cached
    coordinates, or (None, None) if the station list is unavailable.
    """
    stations = tide.get_tide_stations()
    if stations is None or stations.empty:
        return None, None
    lat, lng = check_location.get_coordinates()
    dists = haversine_mi(
        lat, lng, stations['lat'].to_numpy(), stations['lng'].to_numpy()
    )
    i = int(dists.argmin())
    return stations.iloc[i]['name'], float(dists[i])


def is_coastal(threshold_mi=COAST_THRESHOLD_MI):
    """
    True if within `threshold_mi` of a NOAA tide station.

    Defaults to True when proximity can't be determined, since that
    only happens on a station-list fetch failure -- in which case the
    marine sections will report their own 'unavailable' anyway.
    """
    _, dist = nearest_station()
    return True if dist is None else dist <= threshold_mi


def is_in_maine():
    return nws.state() == 'ME'
