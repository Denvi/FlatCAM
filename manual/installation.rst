Installation
============

Windows Installer
-----------------

Download the installer from the repository_ and run it in your machine.
It includes everything you need.

.. _repository: https://bitbucket.org/jpcgt/flatcam/downloads

Ubuntu
------

FlatCAM should work on most Linux distributions but Ubuntu has been
chosen as the test platform.

There are several dependencies required to run FlatCAM. These are
listed in the following section. Before attempting a manual installation,
try running the provided setup script ``setup_ubuntu.sh`` that will
download and install required packages.

OS-X
----

See manual instructions below.


Manual Installation
-------------------

Requirements
~~~~~~~~~~~~

* Python 2.7 32-bit
* PyQt 4
* Matplotlib 1.3.1
* Numpy 1.8
* `Shapely 1.3`_
  * GEOS
* RTree
  * SpatialIndex

.. _Shapely 1.3: https://pypi.python.org/pypi/Shapely

These packages might have their own dependencies.

Linux
~~~~~

Under Linux, most modern package installers like **yum** or **apt-get**
will attempt to locate and install the whole tree of dependencies for a
specified package automatically. Refer to the provided setup script
``setup_ubuntu.sh`` for the names and installation order.

Once the dependencies are installed, download the latest .zip release
(or the latest source, although it is not garanteed to work), unpack it,
change into the created folder and run::

    Python FlatCAM.py


Windows
~~~~~~~

An easy way to get the requirements in your system is to install WinPython_.
This is a standalone distribution of Python which includes all of FlatCAM's
dependencies, except for Shapely and RTree. These can be found here:
`Unofficial Windows Binaries for Python Extension Packages`_.

.. _WinPython: http://winpython.sourceforge.net/
.. _Unofficial Windows Binaries for Python Extension Packages: http://www.lfd.uci.edu/~gohlke/pythonlibs/

Once the dependencies are installed, download the latest .zip
release (or the latest source, although it is not garanteed to work),
unpack it, change into the created folder and run::

    python FlatCAM.py


OS-X
~~~~

Start by installing binary packages: pyqt, geos, spatialindex.
One way to do this is using Homebrew_::

    brew install name_of_package

.. _Homebrew: http://brew.sh

Now you can install all Python packages (numpy, matplotlib, rtree, scipy,
shapely, simplejson) using pip::

    pip install name_of_package

Finally, download the latest FlatCAM .zip package or source code. Change into
its directory and launch it by running::

    python FlatCAM.py

