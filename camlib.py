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

    def convert_units(self, units):
        """
        Converts the units of the object to ``units`` by scaling all
        the geometry appropriately.

        :param units: "IN" or "MM"
        :type units: str
        :return: Scaling factor resulting from unit change.
        :rtype: float
        """

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
        ``self.solid_geometry`` has been converted using the ``to_dict``
        function. Attributes to include are listed in
        ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        return


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
    """

    def __init__(self):
        # Initialize parent
        Geometry.__init__(self)        
        
        # Number format
        self.digits = 3
        """Number of integer digits in Gerber numbers. Used during parsing."""

        self.fraction = 4
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
        self.ser_attrs += ['digits', 'fraction', 'apertures', 'paths',
                           'buffered_paths', 'regions', 'flashes',
                           'flash_geometry']

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

    def fix_regions(self):
        """
        Overwrites the region polygons with fixed
        versions if found to be invalid (according to Shapely).
        """
        for region in self.regions:
            if not region['polygon'].is_valid:
                region['polygon'] = region['polygon'].buffer(0)
    
    def buffer_paths(self):
        self.buffered_paths = []
        for path in self.paths:
            width = self.apertures[path["aperture"]]["size"]
            self.buffered_paths.append(path["linestring"].buffer(width/2))
    
    def aperture_parse(self, gline):
        """
        Parse gerber aperture definition into dictionary of apertures.
        The following kinds and their attributes are supported:

        * *Circular (C)*: size (float)
        * *Rectangle (R)*: width (float), height (float)
        * *Obround (O)*: width (float), height (float). NOTE: This can
          be parsed, but it is not supported further yet.
        """
        indexstar = gline.find("*")
        indexc = gline.find("C,")
        if indexc != -1:  # Circle, example: %ADD11C,0.1*%
            apid = gline[4:indexc]
            self.apertures[apid] = {"type": "C",
                                    "size": float(gline[indexc+2:indexstar])}
            return apid
        indexr = gline.find("R,")
        if indexr != -1:  # Rectangle, example: %ADD15R,0.05X0.12*%
            apid = gline[4:indexr]
            indexx = gline.find("X")
            self.apertures[apid] = {"type": "R",
                                    "width": float(gline[indexr+2:indexx]),
                                    "height": float(gline[indexx+1:indexstar])}
            return apid
        indexo = gline.find("O,")
        if indexo != -1:  # Obround
            apid = gline[4:indexo]
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
        Main Gerber parser.
        """

        # Mode (IN/MM)
        mode_re = re.compile(r'^%MO(IN|MM)\*%$')

        path = []  # Coordinates of the current path
        last_path_aperture = None
        current_aperture = None
        
        for gline in glines:
            
            if gline.find("D01*") != -1:  # pen down
                path.append(coord(gline, self.digits, self.fraction))
                last_path_aperture = current_aperture
                continue
        
            if gline.find("D02*") != -1:  # pen up
                if len(path) > 1:
                    # Path completed, create shapely LineString
                    self.paths.append({"linestring": LineString(path),
                                       "aperture": last_path_aperture})
                path = [coord(gline, self.digits, self.fraction)]
                continue
            
            indexd3 = gline.find("D03*")
            if indexd3 > 0:  # Flash
                self.flashes.append({"loc": coord(gline, self.digits, self.fraction),
                                     "aperture": current_aperture})
                continue
            if indexd3 == 0:  # Flash?
                print "WARNING: Uninplemented flash style:", gline
                continue
            
            if gline.find("G37*") != -1:  # end region
                # Only one path defines region?
                self.regions.append({"polygon": Polygon(path),
                                     "aperture": last_path_aperture})
                path = []
                continue
            
            if gline.find("%ADD") != -1:  # aperture definition
                self.aperture_parse(gline)  # adds element to apertures
                continue
            
            indexstar = gline.find("*")
            if gline.find("D") == 0:  # Aperture change
                current_aperture = gline[1:indexstar]
                continue
            if gline.find("G54D") == 0:  # Aperture change (deprecated)
                current_aperture = gline[4:indexstar]
                continue
            
            if gline.find("%FS") != -1:  # Format statement
                indexx = gline.find("X")
                self.digits = int(gline[indexx + 1])
                self.fraction = int(gline[indexx + 2])
                continue

            # Mode (IN/MM)
            match = mode_re.search(gline)
            if match:
                self.units = match.group(1)
                continue

            print "WARNING: Line ignored:", gline
        
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
            #TODO: Add support for type='O'
            print "WARNING: Aperture type %s not implemented" % (aperture['type'])
    
    def create_geometry(self):
        """
        Geometry from a Gerber file is made up entirely of polygons.
        Every stroke (linear or circular) has an aperture which gives
        it thickness. Additionally, aperture strokes have non-zero area,
        and regions naturally do as well.
        :rtype : None
        @return: None
        """
        # if len(self.buffered_paths) == 0:
        #     self.buffer_paths()
        self.buffer_paths()
        self.fix_regions()
        self.do_flashes()
        self.solid_geometry = cascaded_union(
                                self.buffered_paths + 
                                [poly['polygon'] for poly in self.regions] +
                                self.flash_geometry)


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
        Geometry.__init__(self)
        
        self.tools = {}
        
        self.drills = []

        # Trailing "T" or leading "L"
        self.zeros = ""

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['tools', 'drills', 'zeros']
        
    def parse_file(self, filename):
        efile = open(filename, 'r')
        estr = efile.readlines()
        efile.close()
        self.parse_lines(estr)
        
    def parse_lines(self, elines):
        """
        Main Excellon parser.
        """
        units_re = re.compile(r'^(INCH|METRIC)(?:,([TL])Z)?$')

        current_tool = ""
        
        for eline in elines:
            
            ## Tool definitions ##
            # TODO: Verify all this
            indexT = eline.find("T")
            indexC = eline.find("C")
            indexF = eline.find("F")
            # Type 1
            if indexT != -1 and indexC > indexT and indexF > indexC:
                tool = eline[1:indexC]
                spec = eline[indexC+1:indexF]
                self.tools[tool] = float(spec)
                continue
            # Type 2
            # TODO: Is this inches?
            #indexsp = eline.find(" ")
            #indexin = eline.find("in")
            #if indexT != -1 and indexsp > indexT and indexin > indexsp:
            #    tool = eline[1:indexsp]
            #    spec = eline[indexsp+1:indexin]
            #    self.tools[tool] = spec
            #    continue
            # Type 3
            if indexT != -1 and indexC > indexT:
                tool = eline[1:indexC]
                spec = eline[indexC+1:-1]
                self.tools[tool] = float(spec)
                continue
            
            ## Tool change
            if indexT == 0:
                current_tool = eline[1:-1]
                continue
            
            ## Drill
            indexx = eline.find("X")
            indexy = eline.find("Y")
            if indexx != -1 and indexy != -1:
                x = float(int(eline[indexx+1:indexy])/10000.0)
                y = float(int(eline[indexy+1:-1])/10000.0)
                self.drills.append({'point': Point((x, y)), 'tool': current_tool})
                continue

            # Units and number format
            match = units_re.match(eline)
            if match:
                self.zeros = match.group(2)  # "T" or "L"
                self.units = {"INCH": "IN", "METRIC": "MM"}[match.group(1)]

            print "WARNING: Line ignored:", eline
        
    def create_geometry(self):
        self.solid_geometry = []
        sizes = {}
        for tool in self.tools:
            sizes[tool] = float(self.tools[tool])
        for drill in self.drills:
            poly = Point(drill['point']).buffer(sizes[drill['tool']]/2.0)
            self.solid_geometry.append(poly)
        self.solid_geometry = cascaded_union(self.solid_geometry)

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
            drill.point = affinity.scale(drill.point, factor, factor, origin=(0, 0))

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)

        # Tools
        for tname in self.tools:
            self.tools[tname] *= factor

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
        @param exobj: Excellon object to process
        @type exobj: Excellon
        @param tools: Comma separated tool names
        @type: tools: str
        @return: None
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

    def generate_from_geometry(self, geometry, append=True, tooldia=None):
        """
        Generates G-Code from a Geometry object.
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
                self.gcode += self.polygon2gcode(geo)
                continue
            
            if type(geo) == LineString or type(geo) == LinearRing:
                self.gcode += self.linear2gcode(geo)
                continue
            
            if type(geo) == Point:
                self.gcode += self.point2gcode(geo)
                continue

            if type(geo) == MultiPolygon:
                for poly in geo:
                    self.gcode += self.polygon2gcode(poly)
                continue

            print "WARNING: G-code generation not implemented for %s" % (str(type(geo)))
        
        self.gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        self.gcode += "G00 X0Y0\n"
        self.gcode += "M05\n"  # Spindle stop

    def pre_parse(self, gtext):
        """
        gtext is a single string with g-code
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

        # Results go here
        geometry = []        
        
        # TODO: Merge into single parser?
        gobjs = self.pre_parse(self.gcode)
        
        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}
        
        # Process every instruction
        for gobj in gobjs:
            if 'Z' in gobj:
                if ('X' in gobj or 'Y' in gobj) and gobj['Z'] != current['Z']:
                    print "WARNING: Non-orthogonal motion: From", current
                    print "         To:", gobj
                current['Z'] = gobj['Z']
                
            if 'G' in gobj:
                current['G'] = int(gobj['G'])
                
            if 'X' in gobj or 'Y' in gobj:
                x = 0
                y = 0
                kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow
                
                if 'X' in gobj:
                    x = gobj['X']
                else:
                    x = current['X']
                
                if 'Y' in gobj:
                    y = gobj['Y']
                else:
                    y = current['Y']
                
                if current['Z'] > 0:
                    kind[0] = 'T'
                if current['G'] > 0:
                    kind[1] = 'S'
                   
                arcdir = [None, None, "cw", "ccw"]
                if current['G'] in [0, 1]:  # line
                    geometry.append({'geom': LineString([(current['X'], current['Y']),
                                                        (x, y)]), 'kind': kind})
                if current['G'] in [2, 3]:  # arc
                    center = [gobj['I'] + current['X'], gobj['J'] + current['Y']]
                    radius = sqrt(gobj['I']**2 + gobj['J']**2)
                    start = arctan2(-gobj['J'], -gobj['I'])
                    stop = arctan2(-center[1]+y, -center[0]+x)
                    geometry.append({'geom': arc(center, radius, start, stop,
                                                 arcdir[current['G']],
                                                 self.steps_per_circ),
                                     'kind': kind})

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]
                
        #self.G_geometry = geometry
        self.gcode_parsed = geometry
        return geometry
        
    def plot(self, tooldia=None, dpi=75, margin=0.1,
             color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
             alpha={"T": 0.3, "C": 1.0}):
        """
        Creates a Matplotlib figure with a plot of the
        G-code job.
        """
        if tooldia is None:
            tooldia = self.tooldia
            
        fig = Figure(dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_aspect(1)
        xmin, ymin, xmax, ymax = self.input_geometry_bounds
        ax.set_xlim(xmin-margin, xmax+margin)
        ax.set_ylim(ymin-margin, ymax+margin)
        
        if tooldia == 0:
            for geo in self.gcode_parsed:
                linespec = '--'
                linecolor = color[geo['kind'][0]][1]
                if geo['kind'][0] == 'C':
                    linespec = 'k-'
                x, y = geo['geom'].coords.xy
                ax.plot(x, y, linespec, color=linecolor)
        else:
            for geo in self.gcode_parsed:
                poly = geo['geom'].buffer(tooldia/2.0)
                patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
                                     edgecolor=color[geo['kind'][0]][1],
                                     alpha=alpha[geo['kind'][0]], zorder=2)
                ax.add_patch(patch)
        
        return fig
        
    def plot2(self, axes, tooldia=None, dpi=75, margin=0.1,
             color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
             alpha={"T": 0.3, "C":1.0}):
        """
        Plots the G-code job onto the given axes.
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
                poly = geo['geom'].buffer(tooldia/2.0)
                patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
                                     edgecolor=color[geo['kind'][0]][1],
                                     alpha=alpha[geo['kind'][0]], zorder=2)
                axes.add_patch(patch)
        
    def create_geometry(self):
        self.solid_geometry = cascaded_union([geo['geom'] for geo in self.gcode_parsed])

    def polygon2gcode(self, polygon):
        """
        Creates G-Code for the exterior and all interior paths
        of a polygon.
        @param polygon: A Shapely.Polygon
        @type polygon: Shapely.Polygon
        """
        gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        path = list(polygon.exterior.coords)             # Polygon exterior
        gcode += t % (0, path[0][0], path[0][1])  # Move to first point
        gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
        for pt in path[1:]:
            gcode += t % (1, pt[0], pt[1])    # Linear motion to point
        gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        for ints in polygon.interiors:               # Polygon interiors
            path = list(ints.coords)
            gcode += t % (0, path[0][0], path[0][1])  # Move to first point
            gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
            for pt in path[1:]:
                gcode += t % (1, pt[0], pt[1])    # Linear motion to point
            gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        return gcode

    def linear2gcode(self, linear):
        gcode = ""
        t = "G0%d X%.4fY%.4f\n"
        path = list(linear.coords)
        gcode += t%(0, path[0][0], path[0][1])  # Move to first point
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

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)

        self.z_move *= factor
        self.z_cut *= factor
        self.feedrate *= factor
        self.tooldia *= factor

        return factor


def get_bounds(geometry_set):
    xmin = Inf
    ymin = Inf
    xmax = -Inf
    ymax = -Inf

    print "Getting bounds of:", str(geometry_set)
    for gs in geometry_set:
        gxmin, gymin, gxmax, gymax = geometry_set[gs].bounds()
        xmin = min([xmin, gxmin])
        ymin = min([ymin, gymin])
        xmax = max([xmax, gxmax])
        ymax = max([ymax, gymax])
            
    return [xmin, ymin, xmax, ymax]


def arc(center, radius, start, stop, direction, steps_per_circ):
    """
    Creates a Shapely.LineString for the specified arc.
    @param center: Coordinates of the center [x, y]
    @type center: list
    @param radius: Radius of the arc.
    @type radius: float
    @param start: Starting angle in radians
    @type start: float
    @param stop: End angle in radians
    @type stop: float
    @param direction: Orientation of the arc, "CW" or "CCW"
    @type direction: string
    @param steps_per_circ: Number of straight line segments to
        represent a circle.
    @type steps_per_circ: int
    """
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
        points.append([center[0]+radius*cos(theta), center[1]+radius*sin(theta)])
    return LineString(points)


def clear_poly(poly, tooldia, overlap=0.1):
    """
    Creates a list of Shapely geometry objects covering the inside
    of a Shapely.Polygon. Use for removing all the copper in a region
    or bed flattening.
    @param poly: Target polygon
    @type poly: Shapely.Polygon
    @param tooldia: Diameter of the tool
    @type tooldia: float
    @param overlap: Fraction of the tool diameter to overlap
        in each pass.
    @type overlap: float
    @return list of Shapely.Polygon
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

############### cam.py ####################
def coord(gstr, digits, fraction):
    """
    Parse Gerber coordinates
    """
    global gerbx, gerby
    xindex = gstr.find("X")
    yindex = gstr.find("Y")
    index = gstr.find("D")
    if xindex == -1:
        x = gerbx
        y = int(gstr[(yindex+1):index])*(10**(-fraction))
    elif yindex == -1:
        y = gerby
        x = int(gstr[(xindex+1):index])*(10**(-fraction))
    else:
        x = int(gstr[(xindex+1):yindex])*(10**(-fraction))
        y = int(gstr[(yindex+1):index])*(10**(-fraction))
    gerbx = x
    gerby = y
    return [x, y]
################ end of cam.py #############
