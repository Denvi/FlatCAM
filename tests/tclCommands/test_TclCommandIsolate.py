from FlatCAMObj import FlatCAMGerber


def test_isolate(self):
    """
    Test isolate gerber
    :param self:
    :return:
    """

    self.fc.exec_command_test('open_gerber %s/%s -outname %s'
                              % (self.gerber_files, self.copper_top_filename, self.gerber_top_name))
    gerber_top_obj = self.fc.collection.get_by_name(self.gerber_top_name)
    self.assertTrue(isinstance(gerber_top_obj, FlatCAMGerber), "Expected FlatCAMGerber, instead, %s is %s"
                    % (self.gerber_top_name, type(gerber_top_obj)))

    # isolate traces
    self.fc.exec_command_test('isolate %s -dia %f' % (self.gerber_top_name, self.engraver_diameter))
