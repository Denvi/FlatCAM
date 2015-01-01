Development Planning
====================

Drawing
-------

* [DONE] Arcs
* [DONE] Subtract Shapes
  * [DONE] Selected objects must be kept onlist to preserve order.
* [DONE] Cut Path
  * Polygon to outline
* Force perpendicular
* Un-group (Union creates group)
* Group (But not union)
* [DONE] Remove from index (rebuild index or make deleted instances
  equal to None in the list).
* Better handling/abstraction of geometry types and lists of such.
  * Plotting and extraction of point is now done in a quite
    efficient recursive way.


Algorithms
----------

* [DONE] Reverse path if end is nearer.
* Seed paint: Specify seed.


Features
--------

* Z profile
* UNDO


G-Code
------

* More output options: Formatting.
* Don't lift the tool if unnecessary.


Excellon
--------

* Parse tool definitions in body


Bugs
----

* Unit conversion on opening.
* [DONE] `cascaded_union([])` bug requires more testing.
  * Old version of GEOS


Other
-----

* Unit testing