from FlatCAMObj import FlatCAMGeometry


def test_new_geometry(self):
    """
    Test create new geometry
    :param self:
    :return:
    """

    self.fc.exec_command_test('new_geometry "%s"' % self.geometry_name)
    geometry_obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertTrue(isinstance(geometry_obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                    % (self.geometry_name, type(geometry_obj)))
