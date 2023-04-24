"""
Source: https://github.com/Toblerity/Shapely/blob/master/shapely/ops.py#L489
The modifications below provide a significant performance gain by using an RTree.
"""
import geopandas as gpd
import shapely.ops
from shapely.geometry import GeometryCollection

from spatial_search import RTree


def _split_line_with_multipoint(line, rtree):
    chunks = [line]
    for pt in rtree.get_id(rtree.intersection(line.bounds)):
        new_chunks = []
        for chunk in filter(lambda x: not x.is_empty, chunks):
            # add the newly split 2 lines or the same line if not split
            new_chunks.extend(shapely.ops.split(chunk, pt))
        chunks = new_chunks
    return chunks


def split(geom, splitter):
    """Splits a geometry by another geometry and returns a collection of geometries."""
    if geom.type == 'MultiLineString' and splitter.type == 'MultiPoint':
        rtree = RTree(gpd.GeoDataFrame(geometry=[p for p in splitter]))
        return GeometryCollection([i for part in geom.geoms for i in _split_line_with_multipoint(part, rtree)])
    else:
        return shapely.ops.split(geom, splitter)
