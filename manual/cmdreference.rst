.. _cmdreference:

Shell Command Reference
=======================

.. warning::
    The FlatCAM Shell is under development and its behavior might change in the future. This includes available commands and their syntax.

.. _add_circle:

add_circle
~~~~~~~~~~
Creates a circle in the given Geometry object.

    > add_circle <name> <center_x> <center_y> <radius>
       name: Name of the geometry object to which to append the circle.

       center_x, center_y: Coordinates of the center of the circle.

       radius: Radius of the circle.

.. _add_poly:

add_poly
~~~~~~~~
Creates a polygon in the given Geometry object.

    > create_poly <name> <x0> <y0> <x1> <y1> <x2> <y2> [x3 y3 [...]]
       name: Name of the geometry object to which to append the polygon.

       xi, yi: Coordinates of points in the polygon.

.. _add_rect:

add_rect
~~~~~~~~
Creates a rectange in the given Geometry object.

    > add_rect <name> <botleft_x> <botleft_y> <topright_x> <topright_y>
       name: Name of the geometry object to which to append the rectangle.

       botleft_x, botleft_y: Coordinates of the bottom left corner.

       topright_x, topright_y Coordinates of the top right corner.

cncjob
~~~~~~
Generates a CNC Job from a Geometry Object.

    > cncjob <name> [-z_cut <c>] [-z_move <m>] [-feedrate <f>] [-tooldia <t>] [-outname <n>]
       name: Name of the source object

       z_cut: Z-axis cutting position

       z_move: Z-axis moving position

       feedrate: Moving speed when cutting

       tooldia: Tool diameter to show on screen

       outname: Name of the output object

cutout
~~~~~~
Creates cutout board.

    > cutout <name> [-dia <3.0 (float)>] [-margin <0.0 (float)>] [-gapsize <0.5 (float)>] [-gaps <lr (4|tb|lr)>]
       name: Name of the object

       dia: Tool diameter

       margin: # margin over bounds

       gapsize: size of gap

       gaps: type of gaps

delete
~~~~~~
Deletes the give object.

    > delete <name>
       name: Name of the object to delete.

drillcncjob
~~~~~~~~~~~
Drill CNC job.

    > drillcncjob <name> -tools <str> -drillz <float> -travelz <float> -feedrate <float> -outname <str>
       name: Name of the object

       tools: Comma separated indexes of tools (example: 1,3 or 2)

       drillz: Drill depth into material (example: -2.0)

       travelz: Travel distance above material (example: 2.0)

       feedrate: Drilling feed rate

       outname: Name of object to create

follow
~~~~~~
Creates a geometry object following gerber paths.

    > follow <name> [-outname <oname>]
       name: Name of the gerber object.

       outname: Name of the output geometry object.

.. _geo_union:

geo_union
~~~~~~~~~
Runs a union operation (addition) on the components of the geometry object. For example, if it contains 2 intersecting polygons, this opperation adds them intoa single larger polygon.

    > geo_union <name>
       name: Name of the geometry object.

get_names
~~~~~~~~~
Lists the names of objects in the project.


    > get_names
       No parameters.

help
~~~~
Shows list of commands.

isolate
~~~~~~~
Creates isolation routing geometry for the given Gerber.

    > isolate <name> [-dia <d>] [-passes <p>] [-overlap <o>]
       name: Name of the object

       dia: Tool diameter

       passes: # of tool width

       overlap: Fraction of tool diameter to overlap passes

make_docs
~~~~~~~~~
Prints command rererence in reStructuredText format.

mirror
~~~~~~
Mirror board.

    > mirror <nameMirroredObject> -box <nameOfBox> [-axis <X|Y>]
       name: Name of the object (Gerber or Excellon) to mirror

       box: Name of object which acts as box (cutout for example)

       axis: Axis mirror over X or Y

new
~~~
Starts a new project. Clears objects from memory.


    > new
       No parameters.

.. _new_geometry:

new_geometry
~~~~~~~~~~~~
Creates a new empty geometry object.

    > new_geometry <name>
       name: New object name

.. _offset:

offset
~~~~~~
Changes the position of the object.

    > offset <name> <x> <y>
       name: Name of the object

       x: X-axis distance

       y: Y-axis distance

open_excellon
~~~~~~~~~~~~~
Opens an Excellon file.

    > open_excellon <filename> [-outname <o>]
       filename: Path to file to open.

       outname: Name of the created excellon object.

open_gcode
~~~~~~~~~~
Opens an G-Code file.

    > open_gcode <filename> [-outname <o>]
       filename: Path to file to open.

       outname: Name of the created CNC Job object.

open_gerber
~~~~~~~~~~~
Opens a Gerber file.

    > open_gerber <filename> [-follow <0|1>] [-outname <o>]
       filename: Path to file to open.

       follow: If 1, does not create polygons, just follows the gerber path.

       outname: Name of the created gerber object.

open_project
~~~~~~~~~~~~
Opens a FlatCAM project.

    > open_project <filename>
       filename: Path to file to open.

options
~~~~~~~
Shows the settings for an object.


    > options <name>
       name: Object name.

paint_poly
~~~~~~~~~~
Creates a geometry object with toolpath to cover the inside of a polygon.

    > paint_poly <name> <inside_pt_x> <inside_pt_y> <tooldia> <overlap>
       name: Name of the sourge geometry object.

       inside_pt_x, inside_pt_y: Coordinates of a point inside the polygon.

       tooldia: Diameter of the tool to be used.

       overlap: Fraction of the tool diameter to overlap cuts.

plot
~~~~
Updates the plot on the user interface

save_project
~~~~~~~~~~~~
Saves the FlatCAM project to file.

    > save_project <filename>
       filename: Path to file to save.

.. _scale:

scale
~~~~~
Resizes the object by a factor.

    > scale <name> <factor>
       name: Name of the object

       factor: Fraction by which to scale

set_active
~~~~~~~~~~
Sets a FlatCAM object as active.


    > set_active <name>
       name: Name of the object.

write_gcode
~~~~~~~~~~~
Saves G-code of a CNC Job object to file.

    > write_gcode <name> <filename>
       name: Source CNC Job object

       filename: Output filename
