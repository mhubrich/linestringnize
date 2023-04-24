from rtree import index


class RTree:
    def __init__(self, df, NUM_KNN=10):
        self.NUM_KNN = NUM_KNN
        self.df = df
        self.idx = self.build_rtee(self.df)

    def build_rtee(self, df):
        """Builds an R-Tree of the given geometries in `df`."""
        assert len(df) == df.index.nunique()
        idx = index.Index()
        for i, row in df.iterrows():
            idx.insert(i, row['geometry'].bounds)
        return idx

    def nearest_ids(self, bounds):
        return list(self.idx.nearest(bounds, num_results=self.NUM_KNN))

    def intersection(self, bounds):
        return list(self.idx.intersection(bounds))

    def get_id(self, id):
        return self.df.loc[id, 'geometry']
