import subprocess
import numpy as np

LOCATION_CACHE = 'my_coordinates.txt'

def save_location(lat: float = None, lng: float = None):
    """
    Retrieves the current latitude and longitude, either via IP
    geolocation or manual entry, and caches it to disk.
    Args:
        lat (float): Latitude. If provided with lng, skips IP lookup.
        lng (float): Longitude. If provided with lat, skips IP lookup.
    Returns:
        location (ndarray): Array of [lat, lng] as floats.
    """
    if lat is not None and lng is not None:
        location = np.array([lat, lng])
    else:
        result = subprocess.run(
            'curl -s --max-time 5 https://ipinfo.io | jq \'.loc\'',
            shell=True,
            capture_output=True,
            text=True
        )
        raw = result.stdout.strip().replace('"', '').split(',')
        location = np.array(raw, dtype=float)
    with open(LOCATION_CACHE, 'w') as f:
        f.write(f'{location[0]},{location[1]}')

