import unittest
import camlib

class GerberBuffer(unittest.TestCase):
    def setUp(self):
        self.gerber1 = camlib.Gerber()
        self.gerber1.use_buffer_for_union = True
        self.gerber1.parse_file("./gerber_files/STM32F4-spindle.cmp")
        geometry1 = self.gerber1.solid_geometry
        self.geometry1_area = self.compute_area(geometry1)
        self.gerber2 = camlib.Gerber()
        self.gerber2.use_buffer_for_union = False
        self.gerber2.parse_file("./gerber_files/STM32F4-spindle.cmp")
        geometry2 = self.gerber2.solid_geometry
        self.geometry2_area = self.compute_area (geometry2)

    def compute_area(self, geometry):
        area = 0
        try:
            for geo in geometry:
                area += geo.area

        ## Not iterable, do the actual indexing and add.
        except TypeError:
            area = geometry.area
        return area

    def test_buffer(self):
        self.assertLessEqual(abs(self.geometry2_area - self.geometry1_area), 0.000001)


if __name__ == '__main__':
    unittest.main()
