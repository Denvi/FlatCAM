from FlatCAMObj import FlatCAMExcellon


def test_open_excellon(self):
    """
    Test open excellon file
    :param self:
    :return:
    """

    self.fc.exec_command_test('open_excellon %s/%s -outname %s'
                              % (self.gerber_files, self.excellon_filename, self.excellon_name))
    excellon_obj = self.fc.collection.get_by_name(self.excellon_name)
    self.assertTrue(isinstance(excellon_obj, FlatCAMExcellon), "Expected FlatCAMExcellon, instead, %s is %s"
                    % (self.excellon_name, type(excellon_obj)))
