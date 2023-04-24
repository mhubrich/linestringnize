import argparse
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
from tsp_solver.greedy import solve_tsp as solve_travelling_salesman_problem

import utils
from osm_roads import OSM
from spatial_search import RTree


# Parameters
_EXTEND_BBOX = 100
_LINE_TO_POINTS_INTERVAL = 5.0

# New DataFrame columns
GROUP = "_GROUP"
AGG_IDS = '_AGG_IDS'
AGG_COUNT = '_AGG_COUNT'
AGG_DIST_MIN = '_AGG_DIST_MIN'
AGG_DIST_MAX = '_AGG_DIST_MAX'
AGG_DIST_AVG = '_AGG_DIST_AVG'


def to_string(df, *columns):
    """Converts all `columns` in `df` to string.
      Arguments:
        df: DataFrame.
        columns: Strings. Column names of df.
      Returns:
        DataFrame with `columns` as string type.
    """
    return df.astype({c:str for c in columns})


def merge_values(df, column, sep=','):
    """Concatenates all unique values in `column` of `df`."""
    return sep.join(df[column].unique())


def merge_identical_geometries(df, *columns):
    """Merges `columns` of identical geometries in `df` and then drops duplicates."""
    # Assumes that df.index == range(len(df))
    drop = np.zeros(len(df), dtype=bool)
    grouped = df.assign(wkb=df.geometry.apply(lambda x: x.wkb_hex)).groupby('wkb', sort=False)
    for _, group in grouped.filter(lambda x: len(x) > 1).groupby('wkb', sort=False):
        for column in columns:
            df.loc[group.index[0], column] = merge_values(group, column)
        drop[group.index[1:]] = True
    return df.drop(df.index[drop])


def solve_tsp(df):
    """Solves the travelling salesman problem for all points in `df`.
      Returns a list of integer-location based indexes of the TSP path.
    """
    D = [[utils.distance(df.iloc[i]['geometry'], df.iloc[j]['geometry']) for j in range(i)] \
          for i in range(len(df))]
    return solve_travelling_salesman_problem(D)


def line_to_points(line, interval):
    """Returns a list of Points obtained from a LineString split at every
      `interval` segment. The start and end points of the LineString are
      guaranteed to be included in the list.
    """
    if not isinstance(line, LineString):
        raise ValueError('Argument `line` is expected to be a LineString.')
    length = utils.line_length(line)
    return [line.interpolate(0)] + \
           [line.interpolate(interval/length * i, normalized=True) \
               for i in range(1, int(np.ceil(length/interval)))] + \
           [line.interpolate(1, normalized=True)]


def get_nearest_line_id(geom, osm, interval):
    """Returns the index of the closest line in `osm` to `geom`."""
    if not isinstance(geom, Point) and not isinstance(geom, LineString):
        raise ValueError('Argument `geom` is expected to be a Point or LineString.')
    knn = osm.nearest_ids(geom.bounds)
    if isinstance(geom, Point):
        d = [utils.distance(geom, osm.get_id(id)) for id in knn]
    else:
        sequence = line_to_points(geom, interval)
        d = [sum([utils.distance(p, osm.get_id(id)) for p in sequence]) for id in knn]
    return knn[np.argmin(d)]


def get_nearest_line(geom, osm, interval):
    """Returns the closest line in `osm` to `geom`, where `geom` is a
      Point or LineString.
    """
    return osm.get_id(get_nearest_line_id(geom, osm, interval))


def group_by_block(df, osm):
    """Groups all points in `df` by their street block, separating left and
      right side. Group membership is indicated in column `GROUP`.
    """
    if df.geom_type.nunique() != 1 or df.geom_type.unique()[0] != 'Point':
        raise ValueError('All geometries are expected to be of type Point.')
    df.loc[:, GROUP] = None
    for i, row in df.iterrows():
        line_id = get_nearest_line_id(row['geometry'], osm, _LINE_TO_POINTS_INTERVAL)
        df.loc[i, GROUP] = line_id * utils.side(row['geometry'], osm.get_id(line_id))
    return df


def group_by_locationId(df, locationId):
    """Separates an existing grouping by location codes found in column `locationId`."""
    goup_id = 0
    for _, group in df.groupby([GROUP, locationId], sort=False):
        df.loc[group.index, GROUP] = goup_id
        goup_id += 1
    return df


def group_by_distance(df, max_distance):
    """For an existing grouping, separates points which are further away than
      `max_distance` meters.
    """
    group_id = 0
    for _, group in df.groupby(GROUP, sort=False):
        group_id += 1
        if len(group) == 1:
            df.loc[group.index[0], GROUP] = group_id
        else:
            K = solve_tsp(group)
            for i1, i2 in zip(K, K[1:]):
                df.loc[group.index[i1], GROUP] = group_id
                if utils.distance(group.iloc[i1]['geometry'], group.iloc[i2]['geometry']) > max_distance:
                    group_id += 1
                df.loc[group.index[i2], GROUP] = group_id
    return df


def subline(line, d1, d2, min_length, clipping):
    """Returns a subline of `line` between `d1` and `d2` which has a given
      minimum length. In case (d2-d1) is smaller than the minimum length, the
      subline will be extended. The subline is guaranteed to have a buffer of
      `clipping` from the start and end of `line`.
    """
    sub_line = utils.substring(line, d1, d2)
    sub_line_length = utils.line_length(sub_line)
    if sub_line_length >= min_length:
        return sub_line
    else:
        line_length_deg = line.length / utils.line_length(line)
        diff = min_length - sub_line_length
        diff_deg = line_length_deg * diff
        clipping_deg = line_length_deg * clipping
        res1 = max(0, d2 + diff_deg/2. - line.length)
        res2 = max(0, diff_deg/2. - d1)
        return utils.substring(line, max(clipping_deg, d1 - diff_deg/2. - res1), \
                                     min(line.length-clipping_deg, d2 + diff_deg/2. + res2))


def points_to_line(df):
    """Transforms all points in `df` into a line."""
    return LineString([df.iloc[i]['geometry'] for i in solve_tsp(df)]).simplify(0)


def to_road_line(df, osm, min_length, clipping):
    """Transforms all points in `df` into a line by translating the closest
      sub-line in `osm`.
    """
    line_approx = points_to_line(df) if len(df) > 1 else df.iloc[0]['geometry']
    nearest_road = get_nearest_line(line_approx, osm, _LINE_TO_POINTS_INTERVAL)
    d = [utils.distance(nearest_road, p) for p in df.geometry]
    d1 = nearest_road.project(Point(line_approx.coords[0]))
    d2 = nearest_road.project(Point(line_approx.coords[-1]))
    d1, d2 = min(d1, d2), max(d1, d2)
    sub_road = subline(nearest_road, d1, d2, min_length, clipping)
    m1 = line_approx.interpolate(0.5, normalized=True) if len(df) > 1 else line_approx
    m2 = sub_road.interpolate(sub_road.project(m1))
    return utils.translate(sub_road, m1.x-m2.x, m1.y-m2.y).simplify(0), d


def to_linestring(df, osm, locationId, min_length, clipping, stats=True, child_id=None):
    """Converts all groups of points to a LineString."""
    if df.geom_type.nunique() != 1 or df.geom_type.unique()[0] != 'Point':
        raise ValueError('All geometries are expected to be of type Point.')
    dataframe = {'geometry': [], locationId: []}
    if child_id:
        dataframe[AGG_IDS] = []
    if stats:
        dataframe[AGG_COUNT], dataframe[AGG_DIST_MIN], dataframe[AGG_DIST_MAX], dataframe[AGG_DIST_AVG] = [], [], [], []
    agg_count, agg_dist_min, agg_dist_max, agg_dist_avg, agg_ids = [], [], [], [], []
    for _, group in df.groupby(GROUP, sort=False):
        line, d = to_road_line(group, osm, min_length, clipping)
        dataframe['geometry'].append(line)
        dataframe[locationId].append(merge_values(group, locationId))
        if child_id:
            dataframe[AGG_IDS].append(merge_values(group, child_id))
        if stats:
            dataframe[AGG_COUNT].append(len(d))
            dataframe[AGG_DIST_MIN].append(min(d))
            dataframe[AGG_DIST_MAX].append(max(d))
            dataframe[AGG_DIST_AVG].append(np.mean(d))
    return gpd.GeoDataFrame(dataframe)


def split(line1, line2, threshold):
    """Splits `line1` based on `line2` and returns longest substring.
       If all substrings are shorter than `threshold`, line1 is returned."""
    splits = utils.split(line1, line2)
    if len(splits) == 1:
        return splits[0]
    lengths = map(utils.line_length, splits)
    return line1 if max(lengths) < threshold else splits[np.argmax(lengths)]


def remove_intersections(df, min_length):
    """If there are intersections between lines in `df`, removes the smaller
      part if the larger part is longer than `min_length`.
    """
    if df.geom_type.nunique() != 1 or df.geom_type.unique()[0] != 'LineString':
        raise ValueError('All geometries are expected to be of type LineString.')
    rtree = RTree(df)
    for i, row in df.iterrows():
        ids = rtree.intersection(row['geometry'].bounds)
        ids.remove(i)
        if len(ids) > 0:
            df.loc[i, 'geometry'] = split(row['geometry'],
                                          MultiLineString(list(df.loc[ids, 'geometry'])),
                                          min_length)
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True, type=str,
                        help='path to the input file')
    parser.add_argument('--output', '-o', required=True, type=str,
                        help='path to the output file')
    parser.add_argument('--location_id', '-l', required=False, type=str,
                        default='LocationNumbers',
                        help='name of the location numbers property')
    parser.add_argument('--id', '-I', required=False, type=str,
                        default=None,
                        help='name of the feature ID property')
    parser.add_argument('--max_distance', '-mD', required=False, type=float,
                        default=50.,
                        help='maximum distance between two points to be connected by a line')
    parser.add_argument('--min_length', '-mL', required=False, type=float,
                        default=30.,
                        help='minimum length of a line')
    parser.add_argument('--clipping', '-c', required=False, type=float,
                        default=5.,
                        help='minimum buffer in meter between line start/end and intersection')
    parser.add_argument('--stats', '-s', required=False, type=bool,
                        default=True,
                        help='if true, output file contains statistics on the aggregations')
    args = parser.parse_args()
    df = utils.load_file(args.input)
    df = utils.to_single_geometry(df)
    if args.id:
        ids = [args.location_id, args.id]
    else:
        ids = [args.location_id]
    df = to_string(df, *ids)
    df = merge_identical_geometries(df, *ids)
    df_points, df_other = utils.filter_geometry(df, 'Point')
    df_points_bbox = df_points.total_bounds
    df_points_bbox_extended = utils.shift(df_points_bbox[0], df_points_bbox[1], 225, _EXTEND_BBOX) \
                            + utils.shift(df_points_bbox[2], df_points_bbox[3], 45, _EXTEND_BBOX)
    osm = OSM(df_points_bbox_extended)
    df_points = group_by_block(df_points, osm)
    df_points = group_by_distance(df_points, args.max_distance)
    df_lines = to_linestring(df_points, osm, args.location_id, args.min_length, args.clipping, args.stats, args.id)
    df_lines = remove_intersections(df_lines, 0)
    df_final = utils.concat_dfs(df_lines, df_other)
    utils.save_file(df_final, args.output)
