############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://caram.cl/software/flatcam                         #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from numpy import arctan2, Inf, array, sqrt, pi, ceil, sin, cos
from matplotlib.figure import Figure
import re

# See: http://toblerity.org/shapely/manual.html
from shapely.geometry import Polygon, LineString, Point, LinearRing
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import cascaded_union
import shapely.affinity as affinity
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps
from shapely.geometry.base import BaseGeometry

# Used for solid polygons in Matplotlib
from descartes.patch import PolygonPatch

import simplejson as json
# TODO: Commented for FlatCAM packaging with cx_freeze
#from matplotlib.pyplot import plot


class Geometry:
    def __init__(self):
        # Units (in or mm)
        self.units = 'in'
        
        # Final geometry: MultiPolygon
        self.solid_geometry = None

        # Attributes to be included in serialization
        self.ser_attrs = ['units', 'solid_geometry']
        
    def isolation_geometry(self, offset):
        """
        Creates contours around geometry at a given
        offset distance.

        :param offset: Offset distance.
        :type offset: float
        :return: The buffered geometry.
        :rtype: Shapely.MultiPolygon or Shapely.Polygon
        """
        return self.solid_geometry.buffer(offset)
        
    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        """
        if self.solid_geometry is None:
            print "Warning: solid_geometry not computed yet."
            return (0, 0, 0, 0)
            
        if type(self.solid_geometry) == list:
            # TODO: This can be done faster. See comment from Shapely mailing lists.
            return cascaded_union(self.solid_geometry).bounds
        else:
            return self.solid_geometry.bounds
        
    def size(self):
        """
        Returns (width, height) of rectangular
        bounds of geometry.
        """
        if self.solid_geometry is None:
            print "Warning: solid_geometry not computed yet."
            return 0
        bounds = self.bounds()
        return (bounds[2]-bounds[0], bounds[3]-bounds[1])
        
    def get_empty_area(self, boundary=None):
        """
        Returns the complement of self.solid_geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of self.solid_geometry.
        """
        if boundary is None:
            boundary = self.solid_geometry.envelope
        return boundary.difference(self.solid_geometry)
        
    def clear_polygon(self, polygon, tooldia, overlap=0.15):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.
        """
        poly_cuts = [polygon.buffer(-tooldia/2.0)]
        while True:
            polygon = poly_cuts[-1].buffer(-tooldia*(1-overlap))
            if polygon.area > 0:
                poly_cuts.append(polygon)
            else:
                break
        return poly_cuts

    def scale(self, factor):
        """
        Scales all of the object's geometry by a given factor. Override
        this method.
        :param factor: Number by which to scale.
        :type factor: float
        :return: None
        :rtype: None
        """
        return

    def offset(self, vect):
        """
        Offset the geometry by the given vector. Override this method.

        :param vect: (x, y) vector by which to offset the object.
        :type vect: tuple
        :return: None
        """
        return

    def convert_units(self, units):
        """
        Converts the units of the object to ``units`` by scaling all
        the geometry appropriately. This call ``scale()``. Don't call
        it again in descendents.

        :param units: "IN" or "MM"
        :type units: str
        :return: Scaling factor resulting from unit change.
        :rtype: float
        """
        print "Geometry.convert_units()"

        if units.upper() == self.units.upper():
            return 1.0

        if units.upper() == "MM":
            factor = 25.4
        elif units.upper() == "IN":
            factor = 1/25.4
        else:
            print "Unsupported units:", units
            return 1.0

        self.units = units
        self.scale(factor)
        return factor

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

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])


class Gerber (Geometry):
    """
    **ATTRIBUTES**

    * ``apertures`` (dict): The keys are names/identifiers of each aperture.
      The values are dictionaries key/value pairs which describe the aperture. The
      type key is always present and the rest depend on the key:

    +-----------+-----------------------------------+
    | Key       | Value                             |
    +===========+===================================+
    | type      | (str) "C", "R", or "O"            |
    +-----------+-----------------------------------+
    | others    | Depend on ``type``                |
    +-----------+-----------------------------------+

    * ``paths`` (list): A path is described by a line an aperture that follows that
      line. Each paths[i] is a dictionary:

    +------------+------------------------------------------------+
    | Key        | Value                                          |
    +============+================================================+
    | linestring | (Shapely.LineString) The actual path.          |
    +------------+------------------------------------------------+
    | aperture   | (str) The key for an aperture in apertures.    |
    +------------+------------------------------------------------+

    * ``flashes`` (list): Flashes are single-point strokes of an aperture. Each
      is a dictionary:

    +------------+------------------------------------------------+
    | Key        | Value                                          |
    +============+================================================+
    | loc        | (list) [x (float), y (float)] coordinates.     |
    +------------+------------------------------------------------+
    | aperture   | (str) The key for an aperture in apertures.    |
    +------------+------------------------------------------------+

    * ``regions`` (list): Are surfaces defined by a polygon (Shapely.Polygon),
      which have an exterior and zero or more interiors. An aperture is also
      associated with a region. Each is a dictionary:

    +------------+-----------------------------------------------------+
    | Key        | Value                                               |
    +============+=====================================================+
    | polygon    | (Shapely.Polygon) The polygon defining the region.  |
    +------------+-----------------------------------------------------+
    | aperture   | (str) The key for an aperture in apertures.         |
    +------------+-----------------------------------------------------+

    * ``flash_geometry`` (list): List of (Shapely) geometric object resulting
      from ``flashes``. These are generated from ``flashes`` in ``do_flashes()``.

    * ``buffered_paths`` (list): List of (Shapely) polygons resulting from
      *buffering* (or thickening) the ``paths`` with the aperture. These are
      generated from ``paths`` in ``buffer_paths()``.

    **USAGE**::

        g = Gerber()
        g.parse_file(filename)
        g.create_geometry()
        do_something(s.solid_geometry)


    """

    def __init__(self):
        """
        The constructor takes no parameters. Use ``gerber.parse_files()``
        or ``gerber.parse_lines()`` to populate the object from Gerber source.
        :return: Gerber object
        :rtype: Gerber
        """
        # Initialize parent
        Geometry.__init__(self)        
        
        # Number format
        self.int_digits = 3
        """Number of integer digits in Gerber numbers. Used during parsing."""

        self.frac_digits = 4
        """Number of fraction digits in Gerber numbers. Used during parsing."""
        
        ## Gerber elements ##
        # Apertures {'id':{'type':chr, 
        #             ['size':float], ['width':float],
        #             ['height':float]}, ...}
        self.apertures = {}
        
        # Paths [{'linestring':LineString, 'aperture':str}]
        self.paths = []
        
        # Buffered Paths [Polygon]
        # Paths transformed into Polygons by
        # offsetting the aperture size/2
        self.buffered_paths = []
        
        # Polygon regions [{'polygon':Polygon, 'aperture':str}]
        self.regions = []
        
        # Flashes [{'loc':[float,float], 'aperture':str}]
        self.flashes = []
        
        # Geometry from flashes
        self.flash_geometry = []

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['int_digits', 'frac_digits', 'apertures', 'paths',
                           'buffered_paths', 'regions', 'flashes',
                           'flash_geometry']

        #### Parser patterns ####
        # FS - Format Specification
        # The format of X and Y must be the same!
        # L-omit leading zeros, T-omit trailing zeros
        # A-absolute notation, I-incremental notation
        self.fmt_re = re.compile(r'%FS([LT])([AI])X(\d)(\d)Y\d\d\*%$')

        # Mode (IN/MM)
        self.mode_re = re.compile(r'^%MO(IN|MM)\*%$')

        # Comment G04|G4
        self.comm_re = re.compile(r'^G0?4(.*)$')

        # AD - Aperture definition
        self.ad_re = re.compile(r'^%ADD(\d\d+)([a-zA-Z0-9]*),(.*)\*%$')

        # AM - Aperture Macro
        # Beginning of macro (Ends with *%):
        self.am_re = re.compile(r'^%AM([a-zA-Z0-9]*)\*')

        # Tool change
        # May begin with G54 but that is deprecated
        self.tool_re = re.compile(r'^(?:G54)?D(\d\d+)\*$')

        # G01 - Linear interpolation plus flashes
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        self.lin_re = re.compile(r'^(?:G0?(1))?(?:X(-?\d+))?(?:Y(-?\d+))?(?:D0([123]))?\*$')

        self.setlin_re = re.compile(r'^(?:G0?1)\*')

        # G02/3 - Circular interpolation
        # 2-clockwise, 3-counterclockwise
        self.circ_re = re.compile(r'^(?:G0?([23]))?(?:X(-?\d+))?(?:Y(-?\d+))' +
                                  '?(?:I(-?\d+))?(?:J(-?\d+))?D0([12])\*$')

        # G01/2/3 Occurring without coordinates
        self.interp_re = re.compile(r'^(?:G0?([123]))\*')

        # Single D74 or multi D75 quadrant for circular interpolation
        self.quad_re = re.compile(r'^G7([45])\*$')

        # Region mode on
        # In region mode, D01 starts a region
        # and D02 ends it. A new region can be started again
        # with D01. All contours must be closed before
        # D02 or G37.
        self.regionon_re = re.compile(r'^G36\*$')

        # Region mode off
        # Will end a region and come off region mode.
        # All contours must be closed before D02 or G37.
        self.regionoff_re = re.compile(r'^G37\*$')

        # End of file
        self.eof_re = re.compile(r'^M02\*')

        # IP - Image polarity
        self.pol_re = re.compile(r'^%IP(POS|NEG)\*%$')

        # LP - Level polarity
        self.lpol_re = re.compile(r'^%LP([DC])\*%$')

        # TODO: This is bad.
        self.steps_per_circ = 40

    def scale(self, factor):
        """
        Scales the objects' geometry on the XY plane by a given factor.
        These are:

        * ``apertures``
        * ``paths``
        * ``regions``
        * ``flashes``

        Then ``buffered_paths``, ``flash_geometry`` and ``solid_geometry``
        are re-created with ``self.create_geometry()``.
        :param factor: Number by which to scale.
        :type factor: float
        :rtype : None
        """
        # Apertures
        print "Scaling apertures..."
        for apid in self.apertures:
            for param in self.apertures[apid]:
                if param != "type":  # All others are dimensions.
                    print "Tool:", apid, "Parameter:", param
                    self.apertures[apid][param] *= factor

        # Paths
        print "Scaling paths..."
        for path in self.paths:
            path['linestring'] = affinity.scale(path['linestring'],
                                                factor, factor, origin=(0, 0))

        # Flashes
        print "Scaling flashes..."
        for fl in self.flashes:
            # TODO: Shouldn't 'loc' be a numpy.array()?
            fl['loc'][0] *= factor
            fl['loc'][1] *= factor

        # Regions
        print "Scaling regions..."
        for reg in self.regions:
            reg['polygon'] = affinity.scale(reg['polygon'], factor, factor,
                                            origin=(0, 0))

        # Now buffered_paths, flash_geometry and solid_geometry
        self.create_geometry()

    def offset(self, vect):
        """
        Offsets the objects' geometry on the XY plane by a given vector.
        These are:

        * ``paths``
        * ``regions``
        * ``flashes``

        Then ``buffered_paths``, ``flash_geometry`` and ``solid_geometry``
        are re-created with ``self.create_geometry()``.
        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """

        dx, dy = vect

        # Paths
        print "Shifting paths..."
        for path in self.paths:
            path['linestring'] = affinity.translate(path['linestring'],
                                                    xoff=dx, yoff=dy)

        # Flashes
        print "Shifting flashes..."
        for fl in self.flashes:
            # TODO: Shouldn't 'loc' be a numpy.array()?
            fl['loc'][0] += dx
            fl['loc'][1] += dy

        # Regions
        print "Shifting regions..."
        for reg in self.regions:
            reg['polygon'] = affinity.translate(reg['polygon'],
                                                xoff=dx, yoff=dy)

        # Now buffered_paths, flash_geometry and solid_geometry
        self.create_geometry()

    def fix_regions(self):
        """
        Overwrites the region polygons with fixed
        versions if found to be invalid (according to Shapely).
        """

        for region in self.regions:
            if not region['polygon'].is_valid:
                region['polygon'] = region['polygon'].buffer(0)
    
    def buffer_paths(self):
        """
        This is part of the parsing process. "Thickens" the paths
        by their appertures. This will only work for circular appertures.
        :return: None
        """

        self.buffered_paths = []
        for path in self.paths:
            try:
                width = self.apertures[path["aperture"]]["size"]
                self.buffered_paths.append(path["linestring"].buffer(width/2))
            except KeyError:
                print "ERROR: Failed to buffer path: ", path
                print "Apertures: ", self.apertures
    
    def aperture_parse(self, gline):
        """
        Parse gerber aperture definition into dictionary of apertures.
        The following kinds and their attributes are supported:

        * *Circular (C)*: size (float)
        * *Rectangle (R)*: width (float), height (float)
        * *Obround (O)*: width (float), height (float).

        :param gline: Line of Gerber code known to have an aperture definition.
        :type gline: str
        :return: Identifier of the aperture.
        :rtype: str
        """

        indexstar = gline.find("*")
        indexc = gline.find("C,")
        if indexc != -1:  # Circle, example: %ADD11C,0.1*%
            # Found some Gerber with a leading zero in the aperture id and the
            # referenced it without the zero, so this is a hack to handle that.
            apid = str(int(gline[4:indexc]))
            self.apertures[apid] = {"type": "C",
                                    "size": float(gline[indexc+2:indexstar])}
            return apid
        indexr = gline.find("R,")
        if indexr != -1:  # Rectangle, example: %ADD15R,0.05X0.12*%
            # Hack explained above
            apid = str(int(gline[4:indexr]))
            indexx = gline.find("X")
            self.apertures[apid] = {"type": "R",
                                    "width": float(gline[indexr+2:indexx]),
                                    "height": float(gline[indexx+1:indexstar])}
            return apid
        indexo = gline.find("O,")
        if indexo != -1:  # Obround
            # Hack explained above
            apid = str(int(gline[4:indexo]))
            indexx = gline.find("X")
            self.apertures[apid] = {"type": "O",
                                    "width": float(gline[indexo+2:indexx]),
                                    "height": float(gline[indexx+1:indexstar])}
            return apid
        print "WARNING: Aperture not implemented:", gline
        return None
        
    def parse_file(self, filename):
        """
        Calls Gerber.parse_lines() with array of lines
        read from the given file.
        """
        gfile = open(filename, 'r')
        gstr = gfile.readlines()
        gfile.close()
        self.parse_lines(gstr)
        
    def parse_lines(self, glines):
        """
        Main Gerber parser. Reads Gerber and populates ``self.paths``, ``self.apertures``,
        ``self.flashes``, ``self.regions`` and ``self.units``.

        :param glines: Gerber code as list of strings, each element being
            one line of the source file.
        :type glines: list
        :return: None
        :rtype: None
        """

        path = []  # Coordinates of the current path, each is [x, y]

        last_path_aperture = None
        current_aperture = None

        # 1,2 or 3 from "G01", "G02" or "G03"
        current_interpolation_mode = None

        # 1 or 2 from "D01" or "D02"
        # Note this is to support deprecated Gerber not putting
        # an operation code at the end of every coordinate line.
        current_operation_code = None

        # Current coordinates
        current_x = None
        current_y = None

        # How to interprest circular interpolation: SINGLE or MULTI
        quadrant_mode = None

        line_num = 0
        for gline in glines:
            line_num += 1

            ## G01 - Linear interpolation plus flashes
            # Operation code (D0x) missing is deprecated... oh well I will support it.
            match = self.lin_re.search(gline)
            if match:
                # Dxx alone? Will ignore for now.
                if match.group(1) is None and match.group(2) is None and match.group(3) is None:
                    try:
                        current_operation_code = int(match.group(4))
                    except:
                        pass  # A line with just * will match too.
                    continue

                # Parse coordinates
                if match.group(2) is not None:
                    current_x = parse_gerber_number(match.group(2), self.frac_digits)
                if match.group(3) is not None:
                    current_y = parse_gerber_number(match.group(3), self.frac_digits)

                # Parse operation code
                if match.group(4) is not None:
                    current_operation_code = int(match.group(4))

                # Pen down: add segment
                if current_operation_code == 1:
                    path.append([current_x, current_y])
                    last_path_aperture = current_aperture

                # Pen up: finish path
                elif current_operation_code == 2:
                    if len(path) > 1:
                        if last_path_aperture is None:
                            print "Warning: No aperture defined for curent path. (%d)" % line_num
                        self.paths.append({"linestring": LineString(path),
                                           "aperture": last_path_aperture})
                    path = [[current_x, current_y]]  # Start new path

                # Flash
                elif current_operation_code == 3:
                    self.flashes.append({"loc": [current_x, current_y],
                                         "aperture": current_aperture})

                continue

            ## G02/3 - Circular interpolation
            # 2-clockwise, 3-counterclockwise
            match = self.circ_re.search(gline)
            if match:

                mode, x, y, i, j, d = match.groups()
                try:
                    x = parse_gerber_number(x, self.frac_digits)
                except:
                    x = current_x
                try:
                    y = parse_gerber_number(y, self.frac_digits)
                except:
                    y = current_y
                try:
                    i = parse_gerber_number(i, self.frac_digits)
                except:
                    i = 0
                try:
                    j = parse_gerber_number(j, self.frac_digits)
                except:
                    j = 0

                if quadrant_mode is None:
                    print "ERROR: Found arc without preceding quadrant specification G74 or G75. (%d)" % line_num
                    print gline
                    continue

                if mode is None and current_interpolation_mode not in [2, 3]:
                    print "ERROR: Found arc without circular interpolation mode defined. (%d)" % line_num
                    print gline
                    continue
                elif mode is not None:
                    current_interpolation_mode = int(mode)

                # Set operation code if provided
                if d is not None:
                    current_operation_code = int(d)

                # Nothing created! Pen Up.
                if current_operation_code == 2:
                    print "Warning: Arc with D2. (%d)" % line_num
                    if len(path) > 1:
                        if last_path_aperture is None:
                            print "Warning: No aperture defined for curent path. (%d)" % line_num
                        self.paths.append({"linestring": LineString(path),
                                           "aperture": last_path_aperture})
                    current_x = x
                    current_y = y
                    path = [[current_x, current_y]]  # Start new path
                    continue

                # Flash should not happen here
                if current_operation_code == 3:
                    print "ERROR: Trying to flash within arc. (%d)" % line_num
                    continue

                if quadrant_mode == 'MULTI':
                    center = [i + current_x, j + current_y]
                    radius = sqrt(i**2 + j**2)
                    start = arctan2(-j, -i)
                    stop = arctan2(-center[1] + y, -center[0] + x)
                    arcdir = [None, None, "cw", "ccw"]
                    this_arc = arc(center, radius, start, stop,
                                   arcdir[current_interpolation_mode],
                                   self.steps_per_circ)

                    # Last point in path is current point
                    current_x = this_arc[-1][0]
                    current_y = this_arc[-1][1]

                    # Append
                    path += this_arc

                    last_path_aperture = current_aperture

                    continue

                if quadrant_mode == 'SINGLE':
                    print "Warning: Single quadrant arc are not implemented yet. (%d)" % line_num

            ## G74/75* - Single or multiple quadrant arcs
            match = self.quad_re.search(gline)
            if match:
                if match.group(1) == '4':
                    quadrant_mode = 'SINGLE'
                else:
                    quadrant_mode = 'MULTI'
                continue

            ## G37* - End region
            if self.regionoff_re.search(gline):
                # Only one path defines region?
                if len(path) < 3:
                    print "ERROR: Path contains less than 3 points:"
                    print path
                    print "Line (%d): " % line_num, gline
                    path = []
                    continue

                # For regions we may ignore an aperture that is None
                self.regions.append({"polygon": Polygon(path),
                                     "aperture": last_path_aperture})
                #path = []
                path = [[current_x, current_y]]  # Start new path
                continue
            
            if gline.find("%ADD") != -1:  # aperture definition
                self.aperture_parse(gline)  # adds element to apertures
                continue

            ## G01/2/3* - Interpolation mode change
            # Can occur along with coordinates and operation code but
            # sometimes by itself (handled here).
            # Example: G01*
            match = self.interp_re.search(gline)
            if match:
                current_interpolation_mode = int(match.group(1))
                continue

            ## Tool/aperture change
            # Example: D12*
            match = self.tool_re.search(gline)
            if match:
                current_aperture = match.group(1)
                continue

            ## Number format
            # Example: %FSLAX24Y24*%
            # TODO: This is ignoring most of the format. Implement the rest.
            match = self.fmt_re.search(gline)
            if match:
                self.int_digits = int(match.group(3))
                self.frac_digits = int(match.group(4))
                continue

            ## Mode (IN/MM)
            # Example: %MOIN*%
            match = self.mode_re.search(gline)
            if match:
                self.units = match.group(1)
                continue

            print "WARNING: Line ignored (%d):" % line_num, gline
        
        if len(path) > 1:
            # EOF, create shapely LineString if something still in path
            self.paths.append({"linestring": LineString(path),
                               "aperture": last_path_aperture})

    def do_flashes(self):
        """
        Creates geometry for Gerber flashes (aperture on a single point).
        """

        self.flash_geometry = []
        for flash in self.flashes:
            aperture = self.apertures[flash['aperture']]
            if aperture['type'] == 'C':  # Circles
                circle = Point(flash['loc']).buffer(aperture['size']/2)
                self.flash_geometry.append(circle)
                continue
            if aperture['type'] == 'R':  # Rectangles
                loc = flash['loc']
                width = aperture['width']
                height = aperture['height']
                minx = loc[0] - width/2
                maxx = loc[0] + width/2
                miny = loc[1] - height/2
                maxy = loc[1] + height/2
                rectangle = shply_box(minx, miny, maxx, maxy)
                self.flash_geometry.append(rectangle)
                continue
            if aperture['type'] == 'O':  # Obround
                loc = flash['loc']
                width = aperture['width']
                height = aperture['height']
                if width > height:
                    p1 = Point(loc[0] + 0.5*(width-height), loc[1])
                    p2 = Point(loc[0] - 0.5*(width-height), loc[1])
                    c1 = p1.buffer(height*0.5)
                    c2 = p2.buffer(height*0.5)
                else:
                    p1 = Point(loc[0], loc[1] + 0.5*(height-width))
                    p2 = Point(loc[0], loc[1] - 0.5*(height-width))
                    c1 = p1.buffer(width*0.5)
                    c2 = p2.buffer(width*0.5)
                obround = cascaded_union([c1, c2]).convex_hull
                self.flash_geometry.append(obround)
                continue
            print "WARNING: Aperture type %s not implemented" % (aperture['type'])
    
    def create_geometry(self):
        """
        Geometry from a Gerber file is made up entirely of polygons.
        Every stroke (linear or circular) has an aperture which gives
        it thickness. Additionally, aperture strokes have non-zero area,
        and regions naturally do as well.

        :rtype : None
        :return: None
        """

        # if len(self.buffered_paths) == 0:
        #     self.buffer_paths()
        print "... buffer_paths()"
        self.buffer_paths()
        print "... fix_regions()"
        self.fix_regions()
        print "... do_flashes()"
        self.do_flashes()
        print "... cascaded_union()"
        self.solid_geometry = cascaded_union(self.buffered_paths +
                                             [poly['polygon'] for poly in self.regions] +
                                             self.flash_geometry)

    def get_bounding_box(self, margin=0.0, rounded=False):
        """
        Creates and returns a rectangular polygon bounding at a distance of
        margin from the object's ``solid_geometry``. If margin > 0, the polygon
        can optionally have rounded corners of radius equal to margin.

        :param margin: Distance to enlarge the rectangular bounding
         box in both positive and negative, x and y axes.
        :type margin: float
        :param rounded: Wether or not to have rounded corners.
        :type rounded: bool
        :return: The bounding box.
        :rtype: Shapely.Polygon
        """

        bbox = self.solid_geometry.envelope.buffer(margin)
        if not rounded:
            bbox = bbox.envelope
        return bbox


class Excellon(Geometry):
    """
    *ATTRIBUTES*

    * ``tools`` (dict): The key is the tool name and the value is
      the size (diameter).

    * ``drills`` (list): Each is a dictionary:

    ================  ====================================
    Key               Value
    ================  ====================================
    point             (Shapely.Point) Where to drill
    tool              (str) A key in ``tools``
    ================  ====================================
    """

    def __init__(self):
        """
        The constructor takes no parameters.

        :return: Excellon object.
        :rtype: Excellon
        """

        Geometry.__init__(self)
        
        self.tools = {}
        
        self.drills = []

        # Trailing "T" or leading "L"
        self.zeros = ""

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['tools', 'drills', 'zeros']

        #### Patterns ####
        # Regex basics:
        # ^ - beginning
        # $ - end
        # *: 0 or more, +: 1 or more, ?: 0 or 1

        # M48 - Beggining of Part Program Header
        self.hbegin_re = re.compile(r'^M48$')

        # M95 or % - End of Part Program Header
        # NOTE: % has different meaning in the body
        self.hend_re = re.compile(r'^(?:M95|%)$')

        # FMAT Excellon format
        self.fmat_re = re.compile(r'^FMAT,([12])$')

        # Number format and units
        # INCH uses 6 digits
        # METRIC uses 5/6
        self.units_re = re.compile(r'^(INCH|METRIC)(?:,([TL])Z)?$')

        # Tool definition/parameters (?= is look-ahead
        # NOTE: This might be an overkill!
        self.toolset_re = re.compile(r'^T(0?\d|\d\d)(?=.*C(\d*\.?\d*))?' +
                                     r'(?=.*F(\d*\.?\d*))?(?=.*S(\d*\.?\d*))?' +
                                     r'(?=.*B(\d*\.?\d*))?(?=.*H(\d*\.?\d*))?' +
                                     r'(?=.*Z(-?\d*\.?\d*))?[CFSBHT]')

        # Tool select
        # Can have additional data after tool number but
        # is ignored if present in the header.
        # Warning: This will match toolset_re too.
        self.toolsel_re = re.compile(r'^T((?:\d\d)|(?:\d))')

        # Comment
        self.comm_re = re.compile(r'^;(.*)$')

        # Absolute/Incremental G90/G91
        self.absinc_re = re.compile(r'^G9([01])$')

        # Modes of operation
        # 1-linear, 2-circCW, 3-cirCCW, 4-vardwell, 5-Drill
        self.modes_re = re.compile(r'^G0([012345])')

        # Measuring mode
        # 1-metric, 2-inch
        self.meas_re = re.compile(r'^M7([12])$')

        # Coordinates
        self.xcoord_re = re.compile(r'^X(\d*\.?\d*)(?:Y\d*\.?\d*)?$')
        self.ycoord_re = re.compile(r'^(?:X\d*\.?\d*)?Y(\d*\.?\d*)$')

        # R - Repeat hole (# times, X offset, Y offset)
        self.rep_re = re.compile(r'^R(\d+)(?=.*[XY])+(?:X(\d*\.?\d*))?(?:Y(\d*\.?\d*))?$')

        # Various stop/pause commands
        self.stop_re = re.compile(r'^((G04)|(M09)|(M06)|(M00)|(M30))')
        
    def parse_file(self, filename):
        """
        Reads the specified file as array of lines as
        passes it to ``parse_lines()``.

        :param filename: The file to be read and parsed.
        :type filename: str
        :return: None
        """
        efile = open(filename, 'r')
        estr = efile.readlines()
        efile.close()
        self.parse_lines(estr)
        
    def parse_lines(self, elines):
        """
        Main Excellon parser.

        :param elines: List of strings, each being a line of Excellon code.
        :type elines: list
        :return: None
        """

        current_tool = ""
        in_header = False

        for eline in elines:

            ## Header Begin/End ##
            if self.hbegin_re.search(eline):
                in_header = True
                continue

            if self.hend_re.search(eline):
                in_header = False
                continue

            #### Body ####
            if not in_header:

                ## Tool change ##
                match = self.toolsel_re.search(eline)
                if match:
                    current_tool = str(int(match.group(1)))
                    continue

                ## Drill ##
                indexx = eline.find("X")
                indexy = eline.find("Y")
                if indexx != -1 and indexy != -1:
                    x = float(int(eline[indexx+1:indexy])/10000.0)
                    y = float(int(eline[indexy+1:-1])/10000.0)
                    self.drills.append({'point': Point((x, y)), 'tool': current_tool})
                    continue

            #### Header ####
            if in_header:

                ## Tool definitions ##
                match = self.toolset_re.search(eline)
                if match:
                    name = str(int(match.group(1)))
                    spec = {
                        "C": float(match.group(2)),
                        # "F": float(match.group(3)),
                        # "S": float(match.group(4)),
                        # "B": float(match.group(5)),
                        # "H": float(match.group(6)),
                        # "Z": float(match.group(7))
                    }
                    self.tools[name] = spec
                    continue

                ## Units and number format ##
                match = self.units_re.match(eline)
                if match:
                    self.zeros = match.group(2)  # "T" or "L"
                    self.units = {"INCH": "IN", "METRIC": "MM"}[match.group(1)]
                    continue

            print "WARNING: Line ignored:", eline
        
    def create_geometry(self):
        self.solid_geometry = []

        for drill in self.drills:
            poly = Point(drill['point']).buffer(self.tools[drill['tool']]["C"]/2.0)
            self.solid_geometry.append(poly)

        #self.solid_geometry = cascaded_union(self.solid_geometry)

    def scale(self, factor):
        """
        Scales geometry on the XY plane in the object by a given factor.
        Tool sizes, feedrates an Z-plane dimensions are untouched.

        :param factor: Number by which to scale the object.
        :type factor: float
        :return: None
        :rtype: NOne
        """

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], factor, factor, origin=(0, 0))

        self.create_geometry()

    def offset(self, vect):
        """
        Offsets geometry on the XY plane in the object by a given vector.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """

        dx, dy = vect

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.translate(drill['point'], xoff=dx, yoff=dy)

        self.create_geometry()

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)

        # Tools
        for tname in self.tools:
            self.tools[tname]["C"] *= factor

        self.create_geometry()

        return factor


class CNCjob(Geometry):
    """
    Represents work to be done by a CNC machine.

    *ATTRIBUTES*

    * ``gcode_parsed`` (list): Each is a dictionary:

    =====================  =========================================
    Key                    Value
    =====================  =========================================
    geom                   (Shapely.LineString) Tool path (XY plane)
    kind                   (string) "AB", A is "T" (travel) or
                           "C" (cut). B is "F" (fast) or "S" (slow).
    =====================  =========================================
    """
    def __init__(self, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0):

        Geometry.__init__(self)
        self.kind = kind
        self.units = units
        self.z_cut = z_cut
        self.z_move = z_move
        self.feedrate = feedrate
        self.tooldia = tooldia
        self.unitcode = {"IN": "G20", "MM": "G21"}
        self.pausecode = "G04 P1"
        self.feedminutecode = "G94"
        self.absolutecode = "G90"
        self.gcode = ""
        self.input_geometry_bounds = None
        self.gcode_parsed = None
        self.steps_per_circ = 20  # Used when parsing G-code arcs

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['kind', 'z_cut', 'z_move', 'feedrate', 'tooldia',
                           'gcode', 'input_geometry_bounds', 'gcode_parsed',
                           'steps_per_circ']

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)
        print "CNCjob.convert_units()"

        self.z_cut *= factor
        self.z_move *= factor
        self.feedrate *= factor
        self.tooldia *= factor

        return factor

    def generate_from_excellon(self, exobj):
        """
        Generates G-code for drilling from Excellon object.
        self.gcode becomes a list, each element is a
        different job for each tool in the excellon code.
        """
        self.kind = "drill"
        self.gcode = []
        
        t = "G00 X%.4fY%.4f\n"
        down = "G01 Z%.4f\n" % self.z_cut
        up = "G01 Z%.4f\n" % self.z_move

        for tool in exobj.tools:
            
            points = []
            
            for drill in exobj.drill:
                if drill['tool'] == tool:
                    points.append(drill['point'])
            
            gcode = self.unitcode[self.units.upper()] + "\n"
            gcode += self.absolutecode + "\n"
            gcode += self.feedminutecode + "\n"
            gcode += "F%.2f\n" % self.feedrate
            gcode += "G00 Z%.4f\n" % self.z_move  # Move to travel height
            gcode += "M03\n"  # Spindle start
            gcode += self.pausecode + "\n"
            
            for point in points:
                gcode += t % point
                gcode += down + up
            
            gcode += t % (0, 0)
            gcode += "M05\n"  # Spindle stop
            
            self.gcode.append(gcode)

    def generate_from_excellon_by_tool(self, exobj, tools="all"):
        """
        Creates gcode for this object from an Excellon object
        for the specified tools.

        :param exobj: Excellon object to process
        :type exobj: Excellon
        :param tools: Comma separated tool names
        :type: tools: str
        :return: None
        :rtype: None
        """
        print "Creating CNC Job from Excellon..."
        if tools == "all":
            tools = [tool for tool in exobj.tools]
        else:
            tools = [x.strip() for x in tools.split(",")]
            tools = filter(lambda y: y in exobj.tools, tools)
        print "Tools are:", tools

        points = []
        for drill in exobj.drills:
            if drill['tool'] in tools:
                points.append(drill['point'])

        print "Found %d drills." % len(points)
        #self.kind = "drill"
        self.gcode = []

        t = "G00 X%.4fY%.4f\n"
        down = "G01 Z%.4f\n" % self.z_cut
        up = "G01 Z%.4f\n" % self.z_move

        gcode = self.unitcode[self.units.upper()] + "\n"
        gcode += self.absolutecode + "\n"
        gcode += self.feedminutecode + "\n"
        gcode += "F%.2f\n" % self.feedrate
        gcode += "G00 Z%.4f\n" % self.z_move  # Move to travel height
        gcode += "M03\n"  # Spindle start
        gcode += self.pausecode + "\n"

        for point in points:
            x, y = point.coords.xy
            gcode += t % (x[0], y[0])
            gcode += down + up

        gcode += t % (0, 0)
        gcode += "M05\n"  # Spindle stop

        self.gcode = gcode

    def generate_from_geometry(self, geometry, append=True, tooldia=None, tolerance=0):
        """
        Generates G-Code from a Geometry object. Stores in ``self.gcode``.

        :param geometry: Geometry defining the toolpath
        :type geometry: Geometry
        :param append: Wether to append to self.gcode or re-write it.
        :type append: bool
        :param tooldia: If given, sets the tooldia property but does
            not affect the process in any other way.
        :type tooldia: bool
        :param tolerance: All points in the simplified object will be within the
            tolerance distance of the original geometry.
        :return: None
        :rtype: None
        """
        if tooldia is not None:
            self.tooldia = tooldia
            
        self.input_geometry_bounds = geometry.bounds()
        
        if not append:
            self.gcode = ""

        self.gcode = self.unitcode[self.units.upper()] + "\n"
        self.gcode += self.absolutecode + "\n"
        self.gcode += self.feedminutecode + "\n"
        self.gcode += "F%.2f\n" % self.feedrate
        self.gcode += "G00 Z%.4f\n" % self.z_move  # Move to travel height
        self.gcode += "M03\n"  # Spindle start
        self.gcode += self.pausecode + "\n"
        
        for geo in geometry.solid_geometry:
            
            if type(geo) == Polygon:
                self.gcode += self.polygon2gcode(geo, tolerance=tolerance)
                continue
            
            if type(geo) == LineString or type(geo) == LinearRing:
                self.gcode += self.linear2gcode(geo, tolerance=tolerance)
                continue
            
            if type(geo) == Point:
                self.gcode += self.point2gcode(geo)
                continue

            if type(geo) == MultiPolygon:
                for poly in geo:
                    self.gcode += self.polygon2gcode(poly, tolerance=tolerance)
                continue

            print "WARNING: G-code generation not implemented for %s" % (str(type(geo)))
        
        self.gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        self.gcode += "G00 X0Y0\n"
        self.gcode += "M05\n"  # Spindle stop

    def pre_parse(self, gtext):
        """
        Separates parts of the G-Code text into a list of dictionaries.
        Used by ``self.gcode_parse()``.

        :param gtext: A single string with g-code
        """

        # Units: G20-inches, G21-mm
        units_re = re.compile(r'^G2([01])')

        # TODO: This has to be re-done
        gcmds = []
        lines = gtext.split("\n")  # TODO: This is probably a lot of work!
        for line in lines:
            # Clean up
            line = line.strip()

            # Remove comments
            # NOTE: Limited to 1 bracket pair
            op = line.find("(")
            cl = line.find(")")
            if op > -1 and  cl > op:
                #comment = line[op+1:cl]
                line = line[:op] + line[(cl+1):]

            # Units
            match = units_re.match(line)
            if match:
                self.units = {'0': "IN", '1': "MM"}[match.group(1)]

            # Parse GCode
            # 0   4       12
            # G01 X-0.007 Y-0.057
            # --> codes_idx = [0, 4, 12]
            codes = "NMGXYZIJFP"
            codes_idx = []
            i = 0
            for ch in line:
                if ch in codes:
                    codes_idx.append(i)
                i += 1
            n_codes = len(codes_idx)
            if n_codes == 0:
                continue

            # Separate codes in line
            parts = []
            for p in range(n_codes-1):
                parts.append(line[codes_idx[p]:codes_idx[p+1]].strip())
            parts.append(line[codes_idx[-1]:].strip())

            # Separate codes from values
            cmds = {}
            for part in parts:
                cmds[part[0]] = float(part[1:])
            gcmds.append(cmds)
        return gcmds

    def gcode_parse(self):
        """
        G-Code parser (from self.gcode). Generates dictionary with
        single-segment LineString's and "kind" indicating cut or travel,
        fast or feedrate speed.
        """

        kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        # Results go here
        geometry = []        
        
        # TODO: Merge into single parser?
        gobjs = self.pre_parse(self.gcode)
        
        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}

        # Current path: temporary storage until tool is
        # lifted or lowered.
        path = []

        # Process every instruction
        for gobj in gobjs:

            # Changing height:
            if 'Z' in gobj:
                if ('X' in gobj or 'Y' in gobj) and gobj['Z'] != current['Z']:
                    print "WARNING: Non-orthogonal motion: From", current
                    print "         To:", gobj
                current['Z'] = gobj['Z']
                # Store the path into geometry and reset path
                if len(path) > 1:
                    geometry.append({"geom": LineString(path),
                                     "kind": kind})
                    path = [path[-1]]  # Start with the last point of last path.


            if 'G' in gobj:
                current['G'] = int(gobj['G'])
                
            if 'X' in gobj or 'Y' in gobj:
                
                if 'X' in gobj:
                    x = gobj['X']
                else:
                    x = current['X']
                
                if 'Y' in gobj:
                    y = gobj['Y']
                else:
                    y = current['Y']

                kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

                if current['Z'] > 0:
                    kind[0] = 'T'
                if current['G'] > 0:
                    kind[1] = 'S'
                   
                arcdir = [None, None, "cw", "ccw"]
                if current['G'] in [0, 1]:  # line
                    path.append((x, y))

                if current['G'] in [2, 3]:  # arc
                    center = [gobj['I'] + current['X'], gobj['J'] + current['Y']]
                    radius = sqrt(gobj['I']**2 + gobj['J']**2)
                    start = arctan2(-gobj['J'], -gobj['I'])
                    stop = arctan2(-center[1]+y, -center[0]+x)
                    path += arc(center, radius, start, stop,
                                arcdir[current['G']],
                                self.steps_per_circ)

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]

        self.gcode_parsed = geometry
        return geometry
        
    # def plot(self, tooldia=None, dpi=75, margin=0.1,
    #          color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
    #          alpha={"T": 0.3, "C": 1.0}):
    #     """
    #     Creates a Matplotlib figure with a plot of the
    #     G-code job.
    #     """
    #     if tooldia is None:
    #         tooldia = self.tooldia
    #
    #     fig = Figure(dpi=dpi)
    #     ax = fig.add_subplot(111)
    #     ax.set_aspect(1)
    #     xmin, ymin, xmax, ymax = self.input_geometry_bounds
    #     ax.set_xlim(xmin-margin, xmax+margin)
    #     ax.set_ylim(ymin-margin, ymax+margin)
    #
    #     if tooldia == 0:
    #         for geo in self.gcode_parsed:
    #             linespec = '--'
    #             linecolor = color[geo['kind'][0]][1]
    #             if geo['kind'][0] == 'C':
    #                 linespec = 'k-'
    #             x, y = geo['geom'].coords.xy
    #             ax.plot(x, y, linespec, color=linecolor)
    #     else:
    #         for geo in self.gcode_parsed:
    #             poly = geo['geom'].buffer(tooldia/2.0)
    #             patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
    #                                  edgecolor=color[geo['kind'][0]][1],
    #                                  alpha=alpha[geo['kind'][0]], zorder=2)
    #             ax.add_patch(patch)
    #
    #     return fig
        
    def plot2(self, axes, tooldia=None, dpi=75, margin=0.1,
             color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
             alpha={"T": 0.3, "C": 1.0}, tool_tolerance=0.0005):
        """
        Plots the G-code job onto the given axes.

        :param axes: Matplotlib axes on which to plot.
        :param tooldia: Tool diameter.
        :param dpi: Not used!
        :param margin: Not used!
        :param color: Color specification.
        :param alpha: Transparency specification.
        :param tool_tolerance: Tolerance when drawing the toolshape.
        :return: None
        """
        if tooldia is None:
            tooldia = self.tooldia
        
        if tooldia == 0:
            for geo in self.gcode_parsed:
                linespec = '--'
                linecolor = color[geo['kind'][0]][1]
                if geo['kind'][0] == 'C':
                    linespec = 'k-'
                x, y = geo['geom'].coords.xy
                axes.plot(x, y, linespec, color=linecolor)
        else:
            for geo in self.gcode_parsed:
                poly = geo['geom'].buffer(tooldia/2.0).simplify(tool_tolerance)
                patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
                                     edgecolor=color[geo['kind'][0]][1],
                                     alpha=alpha[geo['kind'][0]], zorder=2)
                axes.add_patch(patch)
        
    def create_geometry(self):
        # TODO: This takes forever. Too much data?
        self.solid_geometry = cascaded_union([geo['geom'] for geo in self.gcode_parsed])

    def polygon2gcode(self, polygon, tolerance=0):
        """
        Creates G-Code for the exterior and all interior paths
        of a polygon.

        :param polygon: A Shapely.Polygon
        :type polygon: Shapely.Polygon
        :param tolerance: All points in the simplified object will be within the
            tolerance distance of the original geometry.
        :type tolerance: float
        :return: G-code to cut along polygon.
        :rtype: str
        """

        if tolerance > 0:
            target_polygon = polygon.simplify(tolerance)
        else:
            target_polygon = polygon

        gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        path = list(target_polygon.exterior.coords)             # Polygon exterior
        gcode += t % (0, path[0][0], path[0][1])  # Move to first point
        gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
        for pt in path[1:]:
            gcode += t % (1, pt[0], pt[1])    # Linear motion to point
        gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        for ints in target_polygon.interiors:               # Polygon interiors
            path = list(ints.coords)
            gcode += t % (0, path[0][0], path[0][1])  # Move to first point
            gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
            for pt in path[1:]:
                gcode += t % (1, pt[0], pt[1])    # Linear motion to point
            gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        return gcode

    def linear2gcode(self, linear, tolerance=0):
        """
        Generates G-code to cut along the linear feature.

        :param linear: The path to cut along.
        :type: Shapely.LinearRing or Shapely.Linear String
        :param tolerance: All points in the simplified object will be within the
            tolerance distance of the original geometry.
        :type tolerance: float
        :return: G-code to cut alon the linear feature.
        :rtype: str
        """

        if tolerance > 0:
            target_linear = linear.simplify(tolerance)
        else:
            target_linear = linear

        gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        path = list(target_linear.coords)
        gcode += t % (0, path[0][0], path[0][1])  # Move to first point
        gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
        for pt in path[1:]:
            gcode += t % (1, pt[0], pt[1])    # Linear motion to point
        gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        return gcode

    def point2gcode(self, point):
        # TODO: This is not doing anything.
        gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        path = list(point.coords)
        gcode += t % (0, path[0][0], path[0][1])  # Move to first point
        gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
        gcode += "G00 Z%.4f\n" % self.z_move      # Stop cutting

    def scale(self, factor):
        """
        Scales all the geometry on the XY plane in the object by the
        given factor. Tool sizes, feedrates, or Z-axis dimensions are
        not altered.

        :param factor: Number by which to scale the object.
        :type factor: float
        :return: None
        :rtype: None
        """

        for g in self.gcode_parsed:
            g['geom'] = affinity.scale(g['geom'], factor, factor, origin=(0, 0))

        self.create_geometry()

    def offset(self, vect):
        """
        Offsets all the geometry on the XY plane in the object by the
        given vector.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """
        dx, dy = vect

        for g in self.gcode_parsed:
            g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)

        self.create_geometry()

def get_bounds(geometry_set):
    xmin = Inf
    ymin = Inf
    xmax = -Inf
    ymax = -Inf

    print "Getting bounds of:", str(geometry_set)
    for gs in geometry_set:
        try:
            gxmin, gymin, gxmax, gymax = geometry_set[gs].bounds()
            xmin = min([xmin, gxmin])
            ymin = min([ymin, gymin])
            xmax = max([xmax, gxmax])
            ymax = max([ymax, gymax])
        except:
            print "DEV WARNING: Tried to get bounds of empty geometry."

    return [xmin, ymin, xmax, ymax]


def arc(center, radius, start, stop, direction, steps_per_circ):
    """
    Creates a list of point along the specified arc.

    :param center: Coordinates of the center [x, y]
    :type center: list
    :param radius: Radius of the arc.
    :type radius: float
    :param start: Starting angle in radians
    :type start: float
    :param stop: End angle in radians
    :type stop: float
    :param direction: Orientation of the arc, "CW" or "CCW"
    :type direction: string
    :param steps_per_circ: Number of straight line segments to
        represent a circle.
    :type steps_per_circ: int
    :return: The desired arc, as list of tuples
    :rtype: list
    """
    # TODO: Resolution should be established by fraction of total length, not angle.

    da_sign = {"cw": -1.0, "ccw": 1.0}
    points = []
    if direction == "ccw" and stop <= start:
        stop += 2*pi
    if direction == "cw" and stop >= start:
        stop -= 2*pi
    
    angle = abs(stop - start)
        
    #angle = stop-start
    steps = max([int(ceil(angle/(2*pi)*steps_per_circ)), 2])
    delta_angle = da_sign[direction]*angle*1.0/steps
    for i in range(steps+1):
        theta = start + delta_angle*i
        points.append((center[0]+radius*cos(theta), center[1]+radius*sin(theta)))
    return points


def clear_poly(poly, tooldia, overlap=0.1):
    """
    Creates a list of Shapely geometry objects covering the inside
    of a Shapely.Polygon. Use for removing all the copper in a region
    or bed flattening.

    :param poly: Target polygon
    :type poly: Shapely.Polygon
    :param tooldia: Diameter of the tool
    :type tooldia: float
    :param overlap: Fraction of the tool diameter to overlap
        in each pass.
    :type overlap: float
    :return: list of Shapely.Polygon
    :rtype: list
    """
    poly_cuts = [poly.buffer(-tooldia/2.0)]
    while True:
        poly = poly_cuts[-1].buffer(-tooldia*(1-overlap))
        if poly.area > 0:
            poly_cuts.append(poly)
        else:
            break
    return poly_cuts


def find_polygon(poly_set, point):
    """
    Return the first polygon in the list of polygons poly_set
    that contains the given point.
    """
    p = Point(point)
    for poly in poly_set:
        if poly.contains(p):
            return poly
    return None


def to_dict(geo):
    output = ''
    if isinstance(geo, BaseGeometry):
        return {
            "__class__": "Shply",
            "__inst__": sdumps(geo)
        }
    return geo


def dict2obj(d):
    if '__class__' in d and '__inst__' in d:
        # For now assume all classes are Shapely geometry.
        return sloads(d['__inst__'])
    else:
        return d


def plotg(geo):
    try:
        _ = iter(geo)
    except:
        geo = [geo]

    for g in geo:
        if type(g) == Polygon:
            x, y = g.exterior.coords.xy
            plot(x, y)
            for ints in g.interiors:
                x, y = ints.coords.xy
                plot(x, y)
            continue

        if type(g) == LineString or type(g) == LinearRing:
            x, y = g.coords.xy
            plot(x, y)
            continue

        if type(g) == Point:
            x, y = g.coords.xy
            plot(x, y, 'o')
            continue

        try:
            _ = iter(g)
            plotg(g)
        except:
            print "Cannot plot:", str(type(g))
            continue

def parse_gerber_number(strnumber, frac_digits):
    """
    Parse a single number of Gerber coordinates.

    :param strnumber: String containing a number in decimal digits
    from a coordinate data block, possibly with a leading sign.
    :type strnumber: str
    :param frac_digits: Number of digits used for the fractional
    part of the number
    :type frac_digits: int
    :return: The number in floating point.
    :rtype: float
    """
    return int(strnumber)*(10**(-frac_digits))

def parse_gerber_coords(gstr, int_digits, frac_digits):
    """
    Parse Gerber coordinates

    :param gstr: Line of G-Code containing coordinates.
    :type gstr: str
    :param int_digits: Number of digits in integer part of a number.
    :type int_digits: int
    :param frac_digits: Number of digits in frac_digits part of a number.
    :type frac_digits: int
    :return: [x, y] coordinates.
    :rtype: list
    """
    global gerbx, gerby
    xindex = gstr.find("X")
    yindex = gstr.find("Y")
    index = gstr.find("D")
    if xindex == -1:
        x = gerbx
        y = int(gstr[(yindex+1):index])*(10**(-frac_digits))
    elif yindex == -1:
        y = gerby
        x = int(gstr[(xindex+1):index])*(10**(-frac_digits))
    else:
        x = int(gstr[(xindex+1):yindex])*(10**(-frac_digits))
        y = int(gstr[(yindex+1):index])*(10**(-frac_digits))
    gerbx = x
    gerby = y
    return [x, y]
