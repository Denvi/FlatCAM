FlatCAM Developer Manual
========================

Options
~~~~~~~

There are **Application Defaults**, **Project Options** and **Object Options** in FlatCAM.

**Application Defaults** are stored in ``app.defaults``. This gets populated (updated) from the ``defaults.json`` file upon startup. These can be edited from the Options tab, where each widget calls ``app.on_options_update()`` if a change is detected. This function iterates over the keys of ``app.defaults`` and reads the GUI elements whose name is ``type + "_app_" key``. Therefore, for an option to be recognized, it must be added to ``defaults.json`` in the first place. When saving, done in ``app.on_file_savedefaults()``, the file is updated, not overwritten.

**Project Options** inherit all options from Application Defaults upon startup. They can be changed thereafter from the UI or by opening a project, which contain previously saved Project Options. These are store in ``app.options`` and can be written and read from the Options tab in the same way as with Application defaults.

**Object Options** for each object are inherited from Project Options upon creation of each new object. They can be modified independently from the Project's options thereafter through the UI, where the widget containing the option is identified by name: ``type + kind + "_" + option``. They are stored in ``object.options``. They are saved along the Project options when saving the project.

The syntax of UI widget names contain a ``type``, which identifies what *type of widget* it is and how its value is supposed to be fetched, and a ``kind``, which refer to what *kind of FlatCAM Object* it is for.

Serialization
~~~~~~~~~~~~~

Serialization refers to converting objects into a form that can be saved in a text file and recontructing objects from a text file.

Saving and loading projects require serialization. These are done in ``App.save_project(filename)`` and ``App.open_project(filename)``.

Serialization in FlatCAM takes 2 forms. The first is calling objects' ``to_dict()`` method, which is inherited from ``Geometry.to_dict()``::

    def to_dict(self):
        """
        Returns a respresentation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d


This creates a dictionary with attributes specified in the object's ``ser_attrs`` list. If these are not in a serialized form, they will be processed later by the function ``to_dict()``::

    def to_dict(geo):
        """
        Makes a Shapely geometry object into serializeable form.

        :param geo: Shapely geometry.
        :type geo: BaseGeometry
        :return: Dictionary with serializable form if ``geo`` was
            BaseGeometry, otherwise returns ``geo``.
        """
        if isinstance(geo, BaseGeometry):
            return {
                "__class__": "Shply",
                "__inst__": sdumps(geo)
            }
        return geo

This is used in ``json.dump(d, f, default=to_dict)`` and is applied to objects that json encounters to be in a non-serialized form.

Geometry Processing
~~~~~~~~~~~~~~~~~~~

