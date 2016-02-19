#import sys
import platform

print "Platform", platform.system(), platform.release()
print "Distro", platform.dist()
print "Python", platform.python_version()


import rtree

print "rtree", rtree.__version__


import shapely
import shapely.geos

print "shapely", shapely.__version__
print "GEOS library", shapely.geos.geos_version


from PyQt4 import Qt

print "Qt", Qt.qVersion()


import numpy

print "Numpy", numpy.__version__


import matplotlib

print "MatPlotLib", matplotlib.__version__
print "MPL Numpy", matplotlib.__version__numpy__