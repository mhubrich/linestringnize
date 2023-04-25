import json
import pyproj
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely.ops
import shapely.affinity
from shapely.geometry import Point, LineString, Polygon


_GEOD = pyproj.Geod(ellps='WGS84')


def GEOD():
    return _GEOD

def load_file(path):
    return gpd.read_file(path).reset_index(drop=True)


def save_file(df, path):
    json.dump(json.loads(df.to_json()), open(path, 'w'))


def filter_geometry(df, geom_type):
    """Filters the GeoDataFrame based on a geometry type."""
    return df[df.geom_type == geom_type], \
           df[df.geom_type != geom_type]


def concat_dfs(df1, df2):
    """Concatenates two DataFrames."""
    return pd.concat([df1, df2], axis=0, ignore_index=True, sort=True)


def shift(lon, lat, deg, dist):
    """Shifts a point by a given distance (meters) into a direction (degrees)."""
    return GEOD().fwd(lon, lat, deg, dist)[:2]


def distance(geom1, geom2):
    """Returns the distance between two geometries in meters."""
    if not isinstance(geom1, Point) or not isinstance(geom2, Point):
        geom1, geom2 = shapely.ops.nearest_points(geom1, geom2)
    return GEOD().inv(geom1.x, geom1.y, geom2.x, geom2.y)[2]


def line_length(l):
    """Returns the total length of a LineString in meters."""
    return sum([distance(Point(p1), Point(p2)) for p1, p2 in zip(l.coords, l.coords[1:])])


def side(p, line):
    """Determines which side of the line `line` the point `p` falls on."""
    l = closest_segment(p, line)
    return np.sign((p.x - l.coords[0][0]) * (l.coords[-1][1] - l.coords[0][1]) \
                 - (p.y - l.coords[0][1]) * (l.coords[-1][0] - l.coords[0][0]))


def to_circle(p, radius, n=36):
    """Returns a circle-like polygon with center `p`."""
    return Polygon([shift(p.x, p.y, i * (360./n), radius) for i in range(n)])


def to_single_geometry(df):
    """Converts all multi geometries into single geometries."""
    rows = []
    for _, row in df.iterrows():
        if row['geometry'].geom_type in ('MultiPoint', 'MultiLineString', 'MultiPolygon'):
            for g in row['geometry']:
                r = row.copy()
                r['geometry'] = g
                rows.append(r)
        else:
            rows.append(row)
    return gpd.GeoDataFrame(rows, index=np.arange(len(rows)))


def closest_segment(point, line):
    """Returns the segment of `line` which is closest to `point`."""
    distance = line.project(point)
    coords = list(line.coords)
    for i, p in enumerate(coords):
        dp = line.project(Point(p))
        if dp == distance:
            if i > 0:
                return LineString((coords[i-1], coords[i]))
            else:
                return LineString((coords[i], coords[i+1]))
        if dp > distance:
            return LineString((coords[i-1], coords[i]))


def substring(geom, start_dist, end_dist, normalized=False):
    """Returns a sub-line between specified distances along a linear geometry."""
    return shapely.ops.substring(geom, start_dist, end_dist, normalized)


def translate(geom, xoff=0.0, yoff=0.0, zoff=0.0):
    """Returns a translated geometry shifted by offsets along each dimension."""
    return shapely.affinity.translate(geom, xoff, yoff, zoff)


def split(geom, splitter):
    """Splits a geometry by another geometry and returns a collection of geometries."""
    return shapely.ops.split(geom, splitter)
