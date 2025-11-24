import unittest
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import utils

class TestUtils(unittest.TestCase):

    def test_is_zip_shapefile(self):
        self.assertTrue(utils.is_zip_shapefile(Path("test.zip")))
        self.assertFalse(utils.is_zip_shapefile(Path("test.gpkg")))

    def test_numeric_columns(self):
        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z'], 'geometry': [Point(0,0), Point(1,1), Point(2,2)]})
        gdf = gpd.GeoDataFrame(df)
        cols = utils.numeric_columns(gdf)
        self.assertEqual(cols, ['a'])

    def test_get_cmap_hexlist(self):
        colors = utils.get_cmap_hexlist("Blues", 5)
        self.assertEqual(len(colors), 5)
        self.assertTrue(all(c.startswith("#") for c in colors))

    def test_make_continuous_legend_html(self):
        html = utils.make_continuous_legend_html(["#ffffff", "#000000"], 0, 100, "Test Label")
        self.assertIn("Test Label", html)
        self.assertIn("0", html)
        self.assertIn("100", html)

if __name__ == '__main__':
    unittest.main()
