from spatial_search import RTree
from query_overpass import query_overpass
from osm_to_geojson import osm_to_geojson


class OSM(RTree):
    def __init__(self, bbox, NUM_KNN=10):
        osm_data = query_overpass(bbox)
        df = osm_to_geojson(osm_data)
        RTree.__init__(self, df, NUM_KNN)
