import os
import json
import requests
import urllib3
urllib3.disable_warnings() # Suppresses InsecureRequestWarning


DEFAULT_ENDPOINT = 'https://overpass-api.de/api/interpreter'
DEFAULT_TIMEOUT = 25
PATH_CACHE = '.tmp'


################################################################################
# blacklists for quering street linestrings
# https://wiki.openstreetmap.org/wiki/Key:highway
blacklist_highway = ['pedestrian', 'track', 'bus_guideway', 'escape', 'raceway',
                     'bridleway', 'steps', 'path', 'cycleway', 'proposed',
                     'bus_stop', 'crossing', 'elevator', 'emergency_access_point',
                     'give_way', 'passing_place', 'speed_camera', 'street_lamp',
                     'stop', 'traffic_signals', 'footway', 'platform', 'service',
                     'corridor']
blacklist_service = ['driveway', 'alley', 'emergency_access', 'drive-through']
blacklist_access = ['no', 'private', 'delivery', 'agricultural', 'forestry']
blacklist_keys = ['area', 'tunnel', 'indoor', 'bridge']
################################################################################


def overpass_post(query, endpoint, timeout):
    payload = {'data': query}
    r = requests.post(endpoint,
                      data=payload,
                      timeout=timeout,
                      verify=False)
    if r.status_code != 200:
        raise ValueError('Unable to retrieve data. Status code: %d.' % r.status_code)
    return r.json()


def build_query(bounds):
    if not hasattr(bounds, '__getitem__') or len(bounds) != 4:
        raise ValueError('`bounds` has to be a tuple of exactly 4 numbers.')
    nodes = 'node({y1},{x1},{y2},{x2});'.format(x1=bounds[0], y1=bounds[1],
                                                x2=bounds[2], y2=bounds[3])
    bl_keys = ''.join(['[!"' + b + '"]' for b in blacklist_keys])
    bl_highway = ''.join(['["highway"!="' + b + '"]' for b in blacklist_highway])
    ways = 'way{bl_keys}["highway"]{bl_highway}({y1},{x1},{y2},{x2});'
    ways = ways.format(x1=bounds[0], y1=bounds[1],
                       x2=bounds[2], y2=bounds[3],
                       bl_keys=bl_keys,
                       bl_highway=bl_highway)
    return '[out:json];(' + nodes + ways + ');out body;>;out body qt;'


def make_filename(bounds):
    if not hasattr(bounds, '__getitem__') or len(bounds) != 4:
        raise ValueError('`bounds` has to be a tuple of exactly 4 numbers.')
    return 'osm_{y1}.{x1}.{y2}.{x2}.json'.format(x1=bounds[0], y1=bounds[1],
                                                 x2=bounds[2], y2=bounds[3])


def query_overpass(bounds, cache=PATH_CACHE,
                           endpoint=DEFAULT_ENDPOINT,
                           timeout=DEFAULT_TIMEOUT):
    if cache and not os.path.isdir(cache):
        os.mkdir(cache)
    if cache and os.path.exists(os.path.join(cache, make_filename(bounds))):
        return json.load(open(os.path.join(cache, make_filename(bounds)), 'r'))
    map = overpass_post(build_query(bounds), endpoint, timeout)
    if cache:
        json.dump(map, open(os.path.join(cache, make_filename(bounds)), 'w'))
    return map
