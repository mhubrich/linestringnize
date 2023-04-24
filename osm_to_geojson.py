import json
import shapely.ops
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon, GeometryCollection

from split import split
from spatial_search import RTree


def to_single(geom):
    """Converts all multi-geometries to single-geometries.
      Arguments:
        geom: shapely geometry.
      Returns:
        A list of Single-geometries.
    """
    if not type(geom) in (Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon, GeometryCollection):
        raise ValueError('Argument `geom` not a known geometry type.')
    if type(geom) in (Point, LineString, Polygon):
        return [geom]
    if type(geom) in (MultiPoint, MultiLineString, MultiPolygon):
        return [x for x in geom]
    if geom.is_empty:
        return [geom]
    else:
        return [y for x in geom for y in to_single(x)]


def get_intersections(lines):
    """Returns all intersections between all given lines.
      Arguments:
        lines: MultiLineString.
      Returns:
        A MultiPoint geometry with all intersections.
    """
    if not isinstance(lines, LineString) and not isinstance(lines, MultiLineString):
        raise ValueError('Argument `lines` is expected to be a (Multi)LineString.')
    if isinstance(lines, MultiLineString):
        lines = to_single(lines)
    intersections = []
    df = gpd.GeoDataFrame(geometry=lines)
    rtree = RTree(df)
    for i, row in df.iterrows():
        ids = rtree.intersection(row['geometry'].bounds)
        ids.remove(i)
        inter = row['geometry'].intersection(MultiLineString(list(rtree.get_id(ids))))
        if not inter.is_empty:
            intersections += to_single(inter)
    # Makes sure that only Points are returned
    assert all(map(lambda x: isinstance(x, Point), intersections))
    return MultiPoint(intersections)


def osm_to_geojson(data):
    """Takes OSM data as input and converts it to a GeoDataFrame.
      Arguments:
        data: Dict or String. The OSM data in JSON format. If String, a JSON
          file at this path is tried to be openend.
      Returns:
        df: GeoDataFrame. Contains all block-wise lines found in `data`.
    """
    if isinstance(data, str):
        data = json.load(open(data, 'r'))
    if not isinstance(data, dict):
        raise ValueError('Argument `data` is expected to be a dictionary.')
    nodes, ways = {}, []
    for obj in data['elements']:
        if obj['type'] == 'node':
            nodes[obj['id']] = Point(obj['lon'], obj['lat'])
        elif obj['type'] == 'way':
            ways.append(obj['nodes'])
    lines = [LineString([nodes[x] for x in w]) for w in ways]
    union = shapely.ops.unary_union(lines)
    merged = shapely.ops.linemerge(union).simplify(0)
    splitted = split(merged, get_intersections(merged))
    return gpd.GeoDataFrame({'geometry': to_single(splitted)})
