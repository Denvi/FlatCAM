from os import listdir

from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry


def test_import_svg(self):
    """
    Test all SVG files inside svg directory.
    Problematic SVG files shold be put there as test reference.
    :param self:
    :return:
    """

    file_list = listdir(self.svg_files)

    for svg_file in file_list:

        # import  without outname
        self.fc.exec_command_test('import_svg "%s/%s"' % (self.svg_files, svg_file))

        obj = self.fc.collection.get_by_name(svg_file)
        self.assertTrue(isinstance(obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                        % (svg_file, type(obj)))

        # import  with outname
        outname = '%s-%s' % (self.geometry_name, svg_file)
        self.fc.exec_command_test('import_svg "%s/%s" -outname "%s"' % (self.svg_files, svg_file, outname))

        obj = self.fc.collection.get_by_name(outname)
        self.assertTrue(isinstance(obj, FlatCAMGeometry), "Expected FlatCAMGeometry, instead, %s is %s"
                        % (outname, type(obj)))

    names = self.fc.collection.get_names()
    self.assertEqual(len(names), len(file_list)*2,
                     "Expected %d objects, found %d" % (len(file_list)*2, len(file_list)))


def test_import_svg_as_geometry(self):

    self.fc.exec_command_test('import_svg "%s/%s" -type geometry -outname "%s"'
                              % (self.svg_files, self.svg_filename, self.geometry_name))

    obj = self.fc.collection.get_by_name(self.geometry_name)
    self.assertTrue(isinstance(obj, FlatCAMGeometry) and not isinstance(obj, FlatCAMGerber),
                    "Expected FlatCAMGeometry, instead, %s is %s" % (self.geometry_name, type(obj)))


def test_import_svg_as_gerber(self):

    self.fc.exec_command_test('import_svg "%s/%s" -type gerber -outname "%s"'
                              % (self.svg_files, self.svg_filename, self.gerber_name))

    obj = self.fc.collection.get_by_name(self.gerber_name)
    self.assertTrue(isinstance(obj, FlatCAMGerber),
                    "Expected FlatCAMGerber, instead, %s is %s" % (self.gerber_name, type(obj)))

    self.fc.exec_command_test('isolate "%s"' % self.gerber_name)
    obj = self.fc.collection.get_by_name(self.gerber_name+'_iso')
    self.assertTrue(isinstance(obj, FlatCAMGeometry),
                    "Expected FlatCAMGeometry, instead, %s is %s" % (self.gerber_name+'_iso', type(obj)))
