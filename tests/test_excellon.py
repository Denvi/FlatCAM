import unittest
import camlib


class ExcellonNumberParseTestInch(unittest.TestCase):

    def test_inch_leading_6digit(self):
        excellon = camlib.Excellon()
        self.assertEqual(excellon.zeros, "L")
        self.assertEqual(excellon.parse_number("123456"), 12.3456)

    def test_inch_leading_5digit(self):
        excellon = camlib.Excellon()
        self.assertEqual(excellon.parse_number("12345"), 12.345)

    def test_inch_leading_15digit(self):
        excellon = camlib.Excellon()
        self.assertEqual(excellon.parse_number("012345"), 1.2345)

    def test_inch_leading_51digit(self):
        excellon = camlib.Excellon()
        self.assertEqual(excellon.parse_number("123450"), 12.345)

    def test_inch_trailing_6digit(self):
        excellon = camlib.Excellon()
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("123456"), 12.3456)

    def test_inch_trailing_5digit(self):
        excellon = camlib.Excellon()
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("12345"), 1.2345)

    def test_inch_trailing_15digit(self):
        excellon = camlib.Excellon()
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("012345"), 1.2345)

    def test_inch_trailing_51digit(self):
        excellon = camlib.Excellon()
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("123450"), 12.345)


class ExcellonNumberParseTestMetric(unittest.TestCase):

    def test_inch_leading_6digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        self.assertEqual(excellon.parse_number("123456"), 123.456)

    def test_inch_leading_5digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        self.assertEqual(excellon.parse_number("12345"), 123.45)

    def test_inch_leading_15digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        self.assertEqual(excellon.parse_number("012345"), 12.345)

    def test_inch_leading_51digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        self.assertEqual(excellon.parse_number("123450"), 123.45)

    def test_inch_trailing_6digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("123456"), 123.456)

    def test_inch_trailing_5digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("12345"), 12.345)

    def test_inch_trailing_15digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("012345"), 12.345)

    def test_inch_trailing_51digit(self):
        excellon = camlib.Excellon()
        excellon.units = "mm"
        excellon.zeros = "T"
        self.assertEqual(excellon.parse_number("123450"), 123.45)


if __name__ == '__main__':
    unittest.main()