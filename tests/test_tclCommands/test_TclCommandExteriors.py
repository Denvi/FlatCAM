from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry


def test_exteriors(self):
    """
    Test exteriors
    :param self:
    :return:
    """

    self.fc.exec_command_test('open_gerber %s/%s -outname %s'
                              % (self.gerber_files, self.cutout_filename, self.gerber_cutout_name))
    gerber_cutout_obj = self.fc.collection.get_by_name(self.gerber_cutout_name)
    self.assertTrue(isinstance(gerber_cutout_obj, FlatCAMGerber), "Expected FlatCAMGerber, instead, %s is %s"
                    % (self.gerber_cutout_name, type(gerber_cutout_obj)))

    # exteriors interiors and delete isolated traces
    self.fc.exec_command_test('isolate %s -dia %f' % (self.gerber_cutout_name, self.engraver_diameter))
    self.fc.exec_command_test('exteriors %s -outname %s'
                              % (self.gerber_cutout_name + '_iso', self.gerber_cutout_name + '_iso_exterior'))
    self.fc.exec_command_test('delete %s' % (self.gerber_cutout_name + '_iso'))
    obj = self.fc.collection.get_by_name(self.gerber_cutout_name + '_iso_exterior')
    self.assertTrue(isinstance(obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                    % (self.gerber_cutout_name + '_iso_exterior', type(obj)))
