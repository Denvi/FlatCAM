from FlatCAMObj import FlatCAMGerber


def test_open_gerber(self):
    """
    Test open gerber file
    :param self:
    :return:
    """

    self.fc.exec_command_test('open_gerber %s/%s -outname %s'
                              % (self.gerber_files, self.copper_top_filename, self.gerber_top_name))
    gerber_top_obj = self.fc.collection.get_by_name(self.gerber_top_name)
    self.assertTrue(isinstance(gerber_top_obj, FlatCAMGerber), "Expected FlatCAMGerber, instead, %s is %s"
                    % (self.gerber_top_name, type(gerber_top_obj)))

    self.fc.exec_command_test('open_gerber %s/%s -outname %s'
                              % (self.gerber_files, self.copper_bottom_filename, self.gerber_bottom_name))
    gerber_bottom_obj = self.fc.collection.get_by_name(self.gerber_bottom_name)
    self.assertTrue(isinstance(gerber_bottom_obj, FlatCAMGerber), "Expected FlatCAMGerber, instead, %s is %s"
                    % (self.gerber_bottom_name, type(gerber_bottom_obj)))

    #just read with  original name
    self.fc.exec_command_test('open_gerber %s/%s'
                              % (self.gerber_files, self.copper_top_filename))
