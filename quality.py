"""
Marine biohazard reporting: active shellfish biotoxin (red-tide /
HAB) closures at and near the location.

Source: Maine Dept. of Marine Resources public ArcGIS service. NOAA's
national HAB system (HABSOS) has no Gulf-of-Maine coverage, so this
section is gated to Maine in main.py.

The closure polygons carry no place name (a single closure can span
much of the coast), so the location is reported as the nearest town
(from NWS) together with whether the point falls inside a closure.
"""
from datetime import datetime, timezone
import api_endpoint as api
import check_location
import nws

DMR_BASE = ('https://gis.maine.gov/mapservices/rest/services/dmr/'
            'DMR_Public_Health_Current_Shellfish_Closures/MapServer')
DMR_DETAILS_URL = 'https://www.maine.gov/dmr/fisheries/shellfish/closures'

# Biotoxin closure layers; species is implied by the layer.
BIOTOXIN_LAYERS = {
    9:  'Soft & hard shell clams',
    10: 'Mussels, oysters, razor/surf clams, snails',
    11: 'All shellfish species',
    12: 'American oyster',
}
SEARCH_RADIUS_MI = 20
ACRES_PER_SQ_MI  = 640


def _epoch_ms_to_date(ms):
    """Format an ArcGIS epoch-milliseconds value as 'MM/DD/YYYY', or
    None if absent."""
    if ms in (None, ''):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime('%m/%d/%Y')


def _active_closures(layer_id, lat, lng, within_mi=None):
    """
    Active biotoxin closures (Status = 'A') for one layer. With
    `within_mi` set, returns closures within that distance of the
    point; otherwise returns only closures containing the point.
    """
    params = {
        'where'         : "Status = 'A'",
        'geometry'      : f'{lng},{lat}',
        'geometryType'  : 'esriGeometryPoint',
        'inSR'          : '4326',
        'spatialRel'    : 'esriSpatialRelIntersects',
        'outFields'     : 'D_APPROVED,ACRES',
        'returnGeometry': 'false',
        'f'             : 'json',
    }
    if within_mi is not None:
        params['distance'] = within_mi
        params['units']    = 'esriSRUnit_StatuteMile'

    data = api.get_json_request(f'{DMR_BASE}/{layer_id}/query', params)
    if not data or 'features' not in data:
        return []
    return [f['attributes'] for f in data['features']]


def _closure_detail(closures):
    """' | N area(s), ~X sq mi | since MM/DD/YYYY' for a species group."""
    count = len(closures)
    acres = sum(c.get('ACRES') or 0 for c in closures)
    sq_mi = acres / ACRES_PER_SQ_MI
    dates = sorted(d for d in
                   (_epoch_ms_to_date(c.get('D_APPROVED')) for c in closures)
                   if d)
    detail = f' | {count} area{"s" if count != 1 else ""}'
    if sq_mi >= 1:
        detail += f', ~{sq_mi:,.0f} sq mi'
    if dates:
        detail += f' | since {dates[0]}'
    return detail


def quality_summary():
    """Biotoxin status at the location plus any closures within range."""
    lat, lng = check_location.get_coordinates()
    town     = nws.location_name() or 'your area'

    here_lines  = []
    nearby_lines = []
    for layer_id, species in BIOTOXIN_LAYERS.items():
        here   = _active_closures(layer_id, lat, lng)
        nearby = _active_closures(layer_id, lat, lng, within_mi=SEARCH_RADIUS_MI)
        if here:
            here_lines.append(f'  {species}{_closure_detail(here)}')
        elif nearby:    # nearby but not at the point
            nearby_lines.append(f'  {species}{_closure_detail(nearby)}')

    content = f'Location: {town}\n\n'
    if here_lines:
        content += ('Your location is within an active biotoxin '
                    '(red-tide) closure:\n' + '\n'.join(here_lines) + '\n')
        if nearby_lines:
            content += ('Also closed within '
                        f'{SEARCH_RADIUS_MI} mi:\n'
                        + '\n'.join(nearby_lines) + '\n')
    elif nearby_lines:
        content += ('No closure at your exact location. Active biotoxin '
                    f'closures within {SEARCH_RADIUS_MI} mi:\n'
                    + '\n'.join(nearby_lines) + '\n')
    else:
        content += (f'No active biotoxin closures within {SEARCH_RADIUS_MI} '
                    'miles. Waters open.\n')
        return content

    content += f'\nFull legal notices: {DMR_DETAILS_URL}\n'
    return content
