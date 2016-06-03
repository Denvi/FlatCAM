from FlatCAMObj import FlatCAMObj
from test_TclCommandOpenExcellon import *


def test_drillcncjob(self):
    """
    Test cncjob
    :param self:
    :return:
    """
    # reuse open excellontests
    test_open_excellon(self)

    self.fc.exec_command_test('drillcncjob %s -tools all -drillz 0.5 -travelz 3 -feedrate 300'
                              % self.excellon_name)
    cam_top_obj = self.fc.collection.get_by_name(self.excellon_name + '_cnc')
    self.assertTrue(isinstance(cam_top_obj, FlatCAMObj), "Expected FlatCAMObj, instead, %s is %s"
                    % (self.excellon_name + '_cnc', type(cam_top_obj)))
