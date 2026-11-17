from django.test import SimpleTestCase

from places.geo import InvalidPolygon, point_in_polygon, validate_polygon

SQUARE = [[0, 0], [0, 10], [10, 10], [10, 0]]
# An L shape: the notch (7,7) is outside.
L_SHAPE = [[0, 0], [10, 0], [10, 5], [5, 5], [5, 10], [0, 10]]


class GeoTests(SimpleTestCase):
    def test_square(self):
        self.assertTrue(point_in_polygon(5, 5, SQUARE))
        self.assertFalse(point_in_polygon(11, 5, SQUARE))
        self.assertFalse(point_in_polygon(5, -1, SQUARE))

    def test_concave_shape(self):
        self.assertTrue(point_in_polygon(2, 8, L_SHAPE))
        self.assertTrue(point_in_polygon(8, 2, L_SHAPE))
        self.assertFalse(point_in_polygon(7, 7, L_SHAPE))

    def test_validate(self):
        self.assertEqual(validate_polygon(SQUARE + [[0, 0]]), [[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0]])
        for bad in ([], [[0, 0], [1, 1]], [[0, 0], [1, 1], [0, 0]], "abc", [[0, 0], [1, 1], [100, 0]],
                    [[0, 0], [1, 1], ["a", 0]], [[0, 0], [1, 1], [1]], [[True, 0], [1, 1], [2, 2]]):
            with self.assertRaises(InvalidPolygon, msg=bad):
                validate_polygon(bad)
