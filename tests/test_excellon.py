import unittest
import camlib


class ExcellonNumberParseTestInch(unittest.TestCase):
    # Inch base format: 00.0000

    # LEADING ZEROS
    # With leading zeros, when you type in a coordinate,
    # the leading zeros must always be included.  Trailing zeros
    # are unneeded and may be left off. The CNC-7 will automatically add them.

    # TRAILING ZEROS
    # You must show all zeros to the right of the number and can omit
    # all zeros to the left of the number. The CNC-7 will count the number
    # of digits you typed and automatically fill in the missing zeros.

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
    # Metric base format: 000.000

    # LEADING ZEROS
    # With leading zeros, when you type in a coordinate,
    # the leading zeros must always be included.  Trailing zeros
    # are unneeded and may be left off. The CNC-7 will automatically add them.

    # TRAILING ZEROS
    # You must show all zeros to the right of the number and can omit
    # all zeros to the left of the number. The CNC-7 will count the number
    # of digits you typed and automatically fill in the missing zeros.

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


class ExcellonFormatM72Test(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        M72
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "in")
        self.assertEqual(self.excellon.zeros, "L")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (90.0, 11.75))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (30.25, 10.5))


class ExcellonFormatM71Test(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        M71
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "mm")
        self.assertEqual(self.excellon.zeros, "L")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (900.0, 117.5))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (302.5, 105.0))


class ExcellonFormatINCHLZTest(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        INCH,LZ
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "in")
        self.assertEqual(self.excellon.zeros, "L")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (90.0, 11.75))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (30.25, 10.5))


class ExcellonFormatINCHTest(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        INCH,LZ
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "in")
        self.assertEqual(self.excellon.zeros, "L")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (90.0, 11.75))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (30.25, 10.5))


class ExcellonFormatINCHTZTest(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        INCH,TZ
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "in")
        self.assertEqual(self.excellon.zeros, "T")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (0.9, 1.175))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (3.025, 1.05))


class ExcellonFormatMETRICLZTest(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        METRIC,LZ
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "mm")
        self.assertEqual(self.excellon.zeros, "L")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (900.0, 117.5))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (302.5, 105.0))


class ExcellonFormatMETRICTest(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        METRIC,LZ
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "mm")
        self.assertEqual(self.excellon.zeros, "L")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (900.0, 117.5))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (302.5, 105.0))


class ExcellonFormatMETRICTZTest(unittest.TestCase):

    def setUp(self):
        self.excellon = camlib.Excellon()
        code = """
        M48
        METRIC,TZ
        T1C.02362F197S550
        T2C.03543F197S550
        M95
        T1
        X9000Y11750
        X30250Y10500
        """
        code = code.split('\n')
        self.excellon.parse_lines(code)

    def test_format(self):
        self.assertEqual(self.excellon.units.lower(), "mm")
        self.assertEqual(self.excellon.zeros, "T")

    def test_coords(self):
        # For X9000 add the missing 00 on the right. Then divide by 10000.
        self.assertEqual(self.excellon.drills[0]["point"].coords[0], (9.0, 11.75))
        self.assertEqual(self.excellon.drills[1]["point"].coords[0], (30.25, 10.5))

if __name__ == '__main__':
    unittest.main()