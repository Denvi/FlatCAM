Basics
======

Source Files
------------

Supported source files are:

* **Gerber**: Typically define copper layers in a circuit board.
* **Excellon**: (drill file): Contain drill specifications, size and coordinates.
* **G-Code**: CNC machine instructions for cutting and/or drilling.

These source files can be loaded by selecting File→Open Gerber…, File→Open Excellon… or File→Open G-Code… respectively. The objects created from source files are automatically added to the current project when loaded.


Objects and Tasks
-----------------

Data in FlatCAM is in the form of 4 different kinds of objects: Gerber, Excellon, Geometry and CNC Job. Gerber, Excellon and CNC Jos objects are directly created by reading files in Gerber, Excellon and G-Code formats. Geometry objects are an intermediate step available to manipulate data. The diagram bellow illustrates the relationship between files and objects. The arrows connecting objects represent a sub-set of the tasks that can be performed in FlatCAM.

.. image:: objects_flow.png
    :align: center


Creating, Saving and Loading Projects
-------------------------------------

A project is everything that you have loaded, created and set inside the program. A new project is created every time you load the program or run File→New.

By running File→Save Project, File→Save Project As… or File→Save a Project Copy… you are saving everything currently in the environment including project options. File→Open Project… lets you load a saved project.


Navigating Plots
----------------

Plots for open objects (Gerber, drills, g-code, etc…) are automatically shown on screen. A plot for a given can be updated by clicking “Update Plot” in the “Selected” tab, in case any parameters that would have changed the plot have been modified.

Zooming plots in and out is accomplished by clicking on the plot and using the mouse **scroll wheel** or hitting one of the following keys:

* ``1``: Fits all graphics to the available plotting area.
* ``2``: Zooms out
* ``3``: Zooms in

When zooming in or out, the point under the cursor stays at the same location.

To scroll left-right or up-down, hold the ``shift`` or ``control`` key respectively while turning the mouse **scroll wheel**.