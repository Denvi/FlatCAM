import os
import tempfile

from test_TclCommandCncjob import *
from test_TclCommandDrillcncjob import *


def test_export_gcodecncjob(self):
    """
    Test cncjob
    :param self:
    :return:
    """

    # reuse tests
    test_cncjob(self)
    test_drillcncjob(self)

    with tempfile.NamedTemporaryFile(prefix='unittest.', suffix="." + self.excellon_name + '.gcode', delete=True)\
            as tmp_file:
        output_filename = tmp_file.name
    self.fc.exec_command_test('write_gcode "%s" "%s"' % (self.excellon_name + '_cnc', output_filename))
    self.assertTrue(os.path.isfile(output_filename))
    os.remove(output_filename)

    with tempfile.NamedTemporaryFile(prefix='unittest.', suffix="." + self.gerber_top_name + '.gcode', delete=True)\
            as tmp_file:
        output_filename = tmp_file.name
    self.fc.exec_command_test('write_gcode "%s" "%s"' % (self.gerber_top_name + '_iso_cnc', output_filename))
    self.assertTrue(os.path.isfile(output_filename))
    os.remove(output_filename)

    # TODO check what is inside files , it should  be same every time