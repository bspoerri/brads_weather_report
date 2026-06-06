import numpy as np

LOCATION_CACHE = 'my_coordinates.txt'

_coordinates = None


def get_coordinates():
    """
    Lazily read the cached [lat, lng] from disk.

    Loading is deferred (rather than done at import time) so that
    save_location() can run first, even though modules that need the
    coordinates are imported before main() executes.
    """
    global _coordinates
    if _coordinates is None:
        try:
            with open(LOCATION_CACHE, 'r') as f:
                raw = f.read().strip().split(',')
            _coordinates = np.array(raw, dtype=float)
        except FileNotFoundError:
            raise FileNotFoundError(
                "Location cache not found. Run save_location() first."
            )
    return _coordinates


def find_nearest(df):
    query_point = get_coordinates()
    test_points = df.loc[:, 'lat':'lng'].to_numpy()
    distances = np.sqrt(np.sum((query_point - test_points)**2, axis=1))
    closest_index_num = np.argsort(distances)[0]
    closest_index_val = df.index[closest_index_num]
    return closest_index_val
