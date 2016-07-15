from FlatCAMObj import FlatCAMGeometry


def test_new(self):
    """
    Test new project
    :param self:
    :return:
    """

    self.fc.exec_command_test('new_geometry "%s"' % self.geometry_name)
    geometry_obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertTrue(isinstance(geometry_obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                    % (self.geometry_name, type(geometry_obj)))

    self.fc.exec_command_test('proc testproc {} { puts "testresult" }')

    result = self.fc.exec_command_test('testproc')

    self.assertEqual(result, "testresult",'testproc should return "testresult"')

    self.fc.exec_command_test('set_sys units MM')
    self.fc.exec_command_test('new')

    # object should not exists anymore
    geometry_obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertIsNone(geometry_obj, "Expected object to be None, instead, %s is %s"
                    % (self.geometry_name, type(geometry_obj)))

    # TODO after new it should  delete all procedures and variables, we need to make sure "testproc" does not exists

    # Test it again  with same names

    self.fc.exec_command_test('set_sys units MM')
    self.fc.exec_command_test('new')

    self.fc.exec_command_test('new_geometry "%s"' % self.geometry_name)
    geometry_obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertTrue(isinstance(geometry_obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                    % (self.geometry_name, type(geometry_obj)))

    self.fc.exec_command_test('set_sys units MM')
    self.fc.exec_command_test('new')

    # object should not exists anymore
    geometry_obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertIsNone(geometry_obj, "Expected object to be None, instead, %s is %s"
                    % (self.geometry_name, type(geometry_obj)))
