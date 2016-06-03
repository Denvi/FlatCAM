from FlatCAMObj import FlatCAMGeometry


def test_add_polygon(self):
    """
    Test add polygon into geometry
    :param self:
    :return:
    """

    self.fc.exec_command_test('new_geometry "%s"' % self.geometry_name)
    geometry_obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertTrue(isinstance(geometry_obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                    % (self.geometry_name, type(geometry_obj)))

    points = '0 0 20 0 10 10 0 10'

    self.fc.exec_command_test('add_polygon "%s" %s' % (self.geometry_name, points))
