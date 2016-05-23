from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry, FlatCAMObj
from test_TclCommandIsolate import *

def test_cncjob(self):
    """
    Test cncjob
    :param self:
    :return:
    """

    # reuse isolate tests
    test_isolate(self)

    self.fc.exec_command_test('cncjob %s_iso -tooldia 0.5 -z_cut 0.05 -z_move 3 -feedrate 300' % self.gerber_top_name)
    cam_top_obj = self.fc.collection.get_by_name(self.gerber_top_name + '_iso_cnc')
    self.assertTrue(isinstance(cam_top_obj, FlatCAMObj), "Expected FlatCAMObj, instead, %s is %s"
                    % (self.gerber_top_name + '_iso_cnc', type(cam_top_obj)))